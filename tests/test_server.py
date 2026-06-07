"""Smoke + edge tests for meok-vehicle-handover-mcp."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone, timedelta

from server import (
    grade_vehicle_condition,
    validate_pod_photo_set,
    compare_collection_delivery,
    apply_bvrla_fair_wear_tear,
    generate_dispute_pack,
    calculate_rha_vs_actual_liability,
    submit_to_bvrla_drs,
    log_ev_soc_handover,
    NAMA_GRADE_DEFINITIONS,
    BVRLA_FAIR_WEAR_RULES,
    POD_PHOTO_RULES,
    OEM_SOC_RULES,
    RHA_LIABILITY_CAP_GBP_PER_TONNE,
)


def _call(tool, **kwargs):
    """FastMCP wraps tools as Tool objects — extract the callable."""
    fn = tool.fn if hasattr(tool, "fn") else tool
    return fn(**kwargs)


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _hours_ago(hours):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


# ──────────────────────────────────────────────────────────────────────
# grade_vehicle_condition
# ──────────────────────────────────────────────────────────────────────

def test_grade_clean_car_is_grade_1():
    r = _call(grade_vehicle_condition,
              panel_damage_list=[],
              vehicle_make_model="Tesla Model 3 2024")
    assert r["nama_grade"] == 1
    assert "No defects reported" in r["justification"][0]


def test_grade_small_dent_is_grade_2():
    r = _call(grade_vehicle_condition,
              panel_damage_list=[
                  {"panel": "ofs_front_door", "type": "dent", "size_mm": 25},
              ],
              vehicle_make_model="BMW 3 Series")
    assert r["nama_grade"] == 2


def test_grade_large_scratch_is_grade_3():
    r = _call(grade_vehicle_condition,
              panel_damage_list=[
                  {"panel": "ofs_rear_quarter", "type": "scratch", "size_mm": 50},
              ])
    assert r["nama_grade"] == 3


def test_grade_three_major_panels_is_grade_4_or_u():
    r = _call(grade_vehicle_condition,
              panel_damage_list=[
                  {"panel": "ofs_front_door", "type": "dent", "size_mm": 50},
                  {"panel": "nrs_rear_door", "type": "scratch", "size_mm": 60},
                  {"panel": "rear_bumper", "type": "crack", "size_mm": 30},
              ])
    assert r["nama_grade"] in (4, "U")
    assert len(r["affected_panels"]) >= 3


def test_grade_paint_chip_within_5mm_stays_grade_1():
    r = _call(grade_vehicle_condition,
              panel_damage_list=[
                  {"panel": "bonnet", "type": "chip", "size_mm": 3},
              ])
    assert r["nama_grade"] == 1


# ──────────────────────────────────────────────────────────────────────
# validate_pod_photo_set
# ──────────────────────────────────────────────────────────────────────

def test_pod_valid_when_20_recent_photos_with_gps_and_resolution():
    photos = [
        {"timestamp": _now_iso(), "gps_lat": 52.0, "gps_lon": -1.0,
         "width_px": 1920, "height_px": 1080}
        for _ in range(22)
    ]
    r = _call(validate_pod_photo_set, photo_metadata=photos)
    assert r["pod_valid"] is True
    assert r["photo_count"] == 22


def test_pod_invalid_when_too_few_photos():
    photos = [
        {"timestamp": _now_iso(), "gps_lat": 52.0, "gps_lon": -1.0,
         "width_px": 1920, "height_px": 1080}
        for _ in range(5)
    ]
    r = _call(validate_pod_photo_set, photo_metadata=photos)
    assert r["pod_valid"] is False
    assert any("minimum" in i for i in r["issues"])


def test_pod_flags_low_resolution():
    photos = [
        {"timestamp": _now_iso(), "gps_lat": 52.0, "gps_lon": -1.0,
         "width_px": 640, "height_px": 480}
        for _ in range(22)
    ]
    r = _call(validate_pod_photo_set, photo_metadata=photos)
    assert r["pod_valid"] is False
    assert any("resolution" in i for i in r["issues"])


def test_pod_flags_missing_gps():
    photos = [
        {"timestamp": _now_iso(), "width_px": 1920, "height_px": 1080}
        for _ in range(22)
    ]
    r = _call(validate_pod_photo_set, photo_metadata=photos)
    assert r["pod_valid"] is False
    assert any("GPS" in i for i in r["issues"])


def test_pod_flags_stale_photos():
    photos = [
        {"timestamp": (datetime.now(timezone.utc) - timedelta(days=14)).isoformat(),
         "gps_lat": 52.0, "gps_lon": -1.0, "width_px": 1920, "height_px": 1080}
        for _ in range(22)
    ]
    r = _call(validate_pod_photo_set, photo_metadata=photos)
    assert r["pod_valid"] is False
    assert any("stale" in i for i in r["issues"])


def test_pod_handles_empty_input():
    r = _call(validate_pod_photo_set, photo_metadata=[])
    assert r["pod_valid"] is False
    assert r["photo_count"] == 0


# ──────────────────────────────────────────────────────────────────────
# compare_collection_delivery
# ──────────────────────────────────────────────────────────────────────

def test_compare_no_change_suggests_pre_existing():
    same = [{"panel": "bonnet", "type": "chip", "size_mm": 3}]
    r = _call(compare_collection_delivery, pod_pre=same, pod_post=same)
    assert r["suggested_liability"] == "pre-existing"
    assert r["new_defects"] == []


def test_compare_multiple_new_defects_suggests_haulier():
    pre = []
    post = [
        {"panel": "ofs_front_door", "type": "dent", "size_mm": 40},
        {"panel": "front_bumper", "type": "scratch", "size_mm": 60},
        {"panel": "rear_bumper", "type": "scratch", "size_mm": 50},
    ]
    r = _call(compare_collection_delivery, pod_pre=pre, pod_post=post)
    assert r["suggested_liability"] == "haulier"
    assert len(r["new_defects"]) == 3


def test_compare_single_new_defect_is_disputed():
    pre = [{"panel": "bonnet", "type": "chip", "size_mm": 3}]
    post = [
        {"panel": "bonnet", "type": "chip", "size_mm": 3},
        {"panel": "ofs_alloy_front", "type": "kerb", "size_mm": 40},
    ]
    r = _call(compare_collection_delivery, pod_pre=pre, pod_post=post)
    assert r["suggested_liability"] == "disputed"
    assert len(r["new_defects"]) == 1


def test_compare_worsened_defect_detected():
    pre = [{"panel": "ofs_front_door", "type": "dent", "size_mm": 10}]
    post = [{"panel": "ofs_front_door", "type": "dent", "size_mm": 40}]
    r = _call(compare_collection_delivery, pod_pre=pre, pod_post=post)
    assert len(r["worsened_defects"]) == 1
    assert r["worsened_defects"][0]["delta_mm"] == 30.0


# ──────────────────────────────────────────────────────────────────────
# apply_bvrla_fair_wear_tear
# ──────────────────────────────────────────────────────────────────────

def test_bvrla_classifies_small_chip_as_fair_wear():
    r = _call(apply_bvrla_fair_wear_tear,
              damage_list=[{"panel": "bonnet", "type": "chip", "size_mm": 4}],
              mileage=20000, age_months=18)
    assert r["fair_wear_tear_count"] == 1
    assert r["chargeable_count"] == 0


def test_bvrla_classifies_large_scratch_as_chargeable():
    r = _call(apply_bvrla_fair_wear_tear,
              damage_list=[{"panel": "ofs_rear_quarter", "type": "scratch", "size_mm": 100}],
              mileage=20000, age_months=18)
    assert r["chargeable_count"] == 1
    assert r["fair_wear_tear_count"] == 0


def test_bvrla_high_mileage_boost_widens_chip_tolerance():
    r_low = _call(apply_bvrla_fair_wear_tear,
                  damage_list=[{"panel": "bonnet", "type": "chip", "size_mm": 6}],
                  mileage=10000, age_months=12)
    r_high = _call(apply_bvrla_fair_wear_tear,
                   damage_list=[{"panel": "bonnet", "type": "chip", "size_mm": 6}],
                   mileage=80000, age_months=48)
    # 6mm chip: low-mileage = chargeable; high-mileage with +2mm boost = fair
    assert r_low["chargeable_count"] == 1
    assert r_high["fair_wear_tear_count"] == 1
    assert r_high["high_mileage_boost_applied"] is True


def test_bvrla_crack_is_chargeable():
    r = _call(apply_bvrla_fair_wear_tear,
              damage_list=[{"panel": "windscreen", "type": "crack", "size_mm": 50}],
              mileage=20000, age_months=18)
    assert r["chargeable_count"] == 1


def test_bvrla_empty_damage_list_returns_zero_both():
    r = _call(apply_bvrla_fair_wear_tear,
              damage_list=[], mileage=0, age_months=0)
    assert r["fair_wear_tear_count"] == 0
    assert r["chargeable_count"] == 0


# ──────────────────────────────────────────────────────────────────────
# generate_dispute_pack
# ──────────────────────────────────────────────────────────────────────

def test_dispute_pack_full_rebuttal_when_no_new_defects():
    same = [{"panel": "bonnet", "type": "chip", "size_mm": 3}]
    r = _call(generate_dispute_pack,
              movement_id="MOV-123",
              vehicle_vrn="AB12CDE",
              pod_pre=same,
              pod_post=same,
              narrative="Operator confirms POD pre/post match.")
    assert r["valid"] is True
    assert "disputed in full" in r["suggested_rebuttal_text"]


def test_dispute_pack_requires_movement_and_vrn():
    r = _call(generate_dispute_pack,
              movement_id="",
              vehicle_vrn="",
              pod_pre=[], pod_post=[], narrative="")
    assert r.get("valid") is False
    assert "required" in r["error"]


def test_dispute_pack_includes_RHA_calc_and_bvrla_classification():
    r = _call(generate_dispute_pack,
              movement_id="MOV-456",
              vehicle_vrn="XY99ABC",
              pod_pre=[],
              pod_post=[{"panel": "rear_bumper", "type": "scratch", "size_mm": 200}],
              narrative="200mm scratch claimed by delivery agent.")
    assert "RHA_liability_calc" in r
    assert "BVRLA_classification" in r
    assert r["RHA_liability_calc"]["cap_gbp_per_tonne"] == 1300


# ──────────────────────────────────────────────────────────────────────
# calculate_rha_vs_actual_liability
# ──────────────────────────────────────────────────────────────────────

def test_rha_cap_calculation_2_tonne_vehicle():
    r = _call(calculate_rha_vs_actual_liability,
              vehicle_value_gbp=40000, vehicle_weight_kg=2000,
              damage_claim_gbp=1500)
    assert r["rha_cap_gbp"] == 2600.0
    assert r["gap_to_actual_gbp"] == 0


def test_rha_recommends_git_for_high_value():
    r = _call(calculate_rha_vs_actual_liability,
              vehicle_value_gbp=100000, vehicle_weight_kg=1800,
              damage_claim_gbp=15000)
    assert r["GIT_recommended"] is True
    assert r["gap_to_actual_gbp"] > 0


def test_rha_invalid_weight_returns_error():
    r = _call(calculate_rha_vs_actual_liability,
              vehicle_value_gbp=40000, vehicle_weight_kg=0,
              damage_claim_gbp=1000)
    assert r["valid"] is False
    assert "weight" in r["error"]


# ──────────────────────────────────────────────────────────────────────
# submit_to_bvrla_drs
# ──────────────────────────────────────────────────────────────────────

def test_drs_submission_accepts_valid_pack():
    pack = _call(generate_dispute_pack,
                 movement_id="MOV-789",
                 vehicle_vrn="LM34NOP",
                 pod_pre=[],
                 pod_post=[{"panel": "ofs_front_door", "type": "dent", "size_mm": 50}],
                 narrative="In-transit dent on offside.")
    r = _call(submit_to_bvrla_drs, dispute_pack=pack)
    assert r["submission_accepted"] is True
    assert r["submission_id"].startswith("BVRLA-DRS-")
    assert r["expected_response_days"] > 0


def test_drs_rejects_missing_pack():
    r = _call(submit_to_bvrla_drs, dispute_pack={})
    assert r["submission_accepted"] is False
    assert "missing" in r["error"]


def test_drs_complex_case_for_many_defects():
    pack = _call(generate_dispute_pack,
                 movement_id="MOV-MULTI",
                 vehicle_vrn="ZZ99ZZZ",
                 pod_pre=[],
                 pod_post=[
                     {"panel": "ofs_front_door", "type": "dent", "size_mm": 50},
                     {"panel": "nrs_front_door", "type": "scratch", "size_mm": 60},
                     {"panel": "bonnet", "type": "chip", "size_mm": 10},
                     {"panel": "rear_bumper", "type": "crack", "size_mm": 30},
                     {"panel": "ofs_alloy_front", "type": "kerb", "size_mm": 40},
                     {"panel": "tailgate", "type": "scratch", "size_mm": 80},
                 ],
                 narrative="Multiple disputed defects.")
    r = _call(submit_to_bvrla_drs, dispute_pack=pack)
    assert r["case_complexity"] == "complex"
    assert r["expected_response_days"] >= 42


# ──────────────────────────────────────────────────────────────────────
# log_ev_soc_handover
# ──────────────────────────────────────────────────────────────────────

def test_soc_tesla_within_band_is_compliant():
    r = _call(log_ev_soc_handover,
              vehicle_id="TES001",
              collection_soc_pct=50,
              delivery_soc_pct=45,
              oem="tesla")
    assert r["oem_compliant"] is True
    assert r["flag_for_dispute"] is False


def test_soc_jlr_above_max_flagged():
    r = _call(log_ev_soc_handover,
              vehicle_id="JLR001",
              collection_soc_pct=70,
              delivery_soc_pct=65,
              oem="jlr")
    # JLR cap is 50% — both pre and post are above
    assert r["oem_compliant"] is False
    assert any("above" in i for i in r["issues"])


def test_soc_in_transit_drain_flags_dispute():
    r = _call(log_ev_soc_handover,
              vehicle_id="BMW001",
              collection_soc_pct=80,
              delivery_soc_pct=50,
              oem="bmw")
    assert r["flag_for_dispute"] is True
    assert r["delta_pct"] == -30.0


def test_soc_unknown_oem_uses_default_band():
    r = _call(log_ev_soc_handover,
              vehicle_id="NEW001",
              collection_soc_pct=50,
              delivery_soc_pct=55,
              oem="NextGenEV")
    assert any("no bundled SoC SLA" in i for i in r["issues"])


def test_soc_out_of_range_input_caught():
    r = _call(log_ev_soc_handover,
              vehicle_id="BAD001",
              collection_soc_pct=120,
              delivery_soc_pct=-5,
              oem="tesla")
    assert any("out of range" in i for i in r["issues"])


# ──────────────────────────────────────────────────────────────────────
# Attestation chain + tables
# ──────────────────────────────────────────────────────────────────────

def test_attestation_carries_ts_sig_issuer_version():
    r = _call(grade_vehicle_condition, panel_damage_list=[], vehicle_make_model="X")
    assert "ts" in r and "sig" in r and "issuer" in r and "version" in r
    assert r["issuer"] == "meok-vehicle-handover-mcp"
    assert r["version"] == "1.0.0"


def test_nama_grade_table_has_five_plus_unclassified():
    keys = set(NAMA_GRADE_DEFINITIONS.keys())
    assert {1, 2, 3, 4, 5, "U"} <= keys


def test_oem_soc_table_has_major_brands():
    assert set(OEM_SOC_RULES.keys()) >= {"tesla", "jlr", "bmw", "mg_saic", "stellantis", "byd"}


def test_rha_cap_constant_is_1300():
    assert RHA_LIABILITY_CAP_GBP_PER_TONNE == 1300


def test_bvrla_rules_table_has_core_thresholds():
    assert "stone_chip_max_mm" in BVRLA_FAIR_WEAR_RULES
    assert "scratch_polishable_max_mm" in BVRLA_FAIR_WEAR_RULES
    assert "alloy_kerb_minor_max_mm" in BVRLA_FAIR_WEAR_RULES


def test_pod_rules_table_has_required_keys():
    assert "min_photos_per_vehicle" in POD_PHOTO_RULES
    assert "min_width_px" in POD_PHOTO_RULES
    assert "max_age_days" in POD_PHOTO_RULES
    assert "require_gps" in POD_PHOTO_RULES


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
