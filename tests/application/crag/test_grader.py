"""Test RelevanceGrader bằng AI giả (mock) — không gọi AI thật.

Ta test LOGIC của grade (ghép prompt + parse output), không test bản thân LLM.
Vì vậy thay LLM thật bằng AsyncMock đã dặn sẵn câu trả lời.
"""

import asyncio
from unittest.mock import AsyncMock

from app.application.crag.grader import RelevanceGrader


def test_grade_yes_thi_True():
    llm = AsyncMock()                 # AI giả
    llm.chat.return_value = "yes"     # dặn: ai gọi chat() thì trả "yes"
    grader = RelevanceGrader(llm)     # tiêm AI giả vào

    # asyncio.run = chạy hàm async từ test thường, chờ lấy kết quả
    ket_qua = asyncio.run(
        grader.grade("GPT-4 bao nhiêu tham số?", "GPT-4 có 1.7 nghìn tỷ tham số")
    )

    assert ket_qua is True            # phải đúng True, sai thì test fail


def test_grade_no_thi_False():
    llm = AsyncMock()
    llm.chat.return_value = "no"
    grader = RelevanceGrader(llm)

    ket_qua = asyncio.run(
        grader.grade("GPT-4 bao nhiêu tham số?", "cảm ơn đã xem video")
    )

    assert ket_qua is False


def test_grade_output_lon_xon_van_dung():
    llm = AsyncMock()
    llm.chat.return_value = "  Yes.\n"   # AI trả lộn xộn: hoa, chấm, khoảng trắng
    grader = RelevanceGrader(llm)

    ket_qua = asyncio.run(grader.grade("q", "doc"))

    assert ket_qua is True               # vẫn True nhờ .strip().lower().startswith("y")


def test_grade_goi_llm_dung_1_lan():
    # Kiểm tra grade thực sự gọi LLM (không "ăn gian" trả bừa).
    llm = AsyncMock()
    llm.chat.return_value = "yes"
    grader = RelevanceGrader(llm)

    asyncio.run(grader.grade("q", "doc"))

    llm.chat.assert_awaited_once()       # chat() được await đúng 1 lần
