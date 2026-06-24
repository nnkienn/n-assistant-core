"""Test decide_verdict — logic thuần, chỉ truyền số, kiểm tra ra verdict đúng."""

from app.application.crag.decision import decide_verdict


def test_khong_co_chunk_tot_thi_INCORRECT():
    assert decide_verdict(n_relevant=0, n_candidates=10) == "INCORRECT"


def test_khong_co_candidate_nao_thi_INCORRECT():
    # Chia cho 0 sẽ lỗi — phải chặn trước. Kho rỗng → INCORRECT.
    assert decide_verdict(n_relevant=0, n_candidates=0) == "INCORRECT"


def test_da_so_tot_thi_CORRECT():
    assert decide_verdict(n_relevant=8, n_candidates=10) == "CORRECT"


def test_dung_nguong_mot_nua_thi_CORRECT():
    # 5/10 = 0.5, đúng ngưỡng _CORRECT_RATIO → vẫn CORRECT.
    assert decide_verdict(n_relevant=5, n_candidates=10) == "CORRECT"


def test_co_nhung_mong_thi_AMBIGUOUS():
    assert decide_verdict(n_relevant=2, n_candidates=10) == "AMBIGUOUS"


def test_chi_mot_chunk_tot_thi_AMBIGUOUS():
    assert decide_verdict(n_relevant=1, n_candidates=10) == "AMBIGUOUS"
