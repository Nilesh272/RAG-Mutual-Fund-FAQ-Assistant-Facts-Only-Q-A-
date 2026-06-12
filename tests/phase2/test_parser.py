from phases.phase1_corpus.scraping.models import ScrapeResult
from phases.phase2_rag_core.parsing.groww_parser import GrowwParser


def test_parse_extracts_key_sections(sample_html: str) -> None:
    parser = GrowwParser()
    result = ScrapeResult(
        source_id="hdfc-large-cap-direct-growth",
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        status="success",
        http_status=200,
        html=sample_html,
        content_hash="hash123",
        fetched_at="2026-06-05T09:15:12+05:30",
    )
    scheme_meta = {
        "scheme_name": "HDFC Large Cap Fund Direct Growth",
        "scheme_category": "large-cap",
    }

    sections = parser.parse(result, scheme_meta)
    section_keys = {section.section_key for section in sections}

    assert "expense_ratio" in section_keys
    assert "exit_load" in section_keys
    assert "minimum_investment" in section_keys
    assert "riskometer" in section_keys
    assert "benchmark" in section_keys


def test_parse_groww_fund_details_metrics() -> None:
    parser = GrowwParser()
    html = """
    <html><body>
      <div class="fundDetails_gap4__kM__Q">Expense ratio 0.99%</div>
      <div class="fundDetails_gap4__kM__Q">Min. for SIP ₹100</div>
      <h5>Expense ratio</h5>
      <p>A fee payable to a mutual fund house for managing your mutual fund investments.</p>
      <div class="exitLoadStampDutyTax_summary">
        Exit load Exit load of 1% if redeemed within 1 year
      </div>
      <div class="investmentObjective_benchmarkRow__tpudX">
        <span>Fund benchmark</span><span>NIFTY 100 Total Return Index</span>
      </div>
    </body></html>
    """
    result = ScrapeResult(
        source_id="hdfc-large-cap-direct-growth",
        url="https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        status="success",
        http_status=200,
        html=html,
        content_hash="hash-groww",
        fetched_at="2026-06-11T09:15:12+05:30",
    )
    sections = parser.parse(
        result,
        {"scheme_name": "HDFC Large Cap Fund Direct Growth", "scheme_category": "large-cap"},
    )
    by_key = {s.section_key: s.content for s in sections}
    assert "0.99%" in by_key["expense_ratio"]
    assert "fee payable" not in by_key["expense_ratio"].lower()
    assert "Rs 100" in by_key["minimum_investment"] or "₹100" in by_key["minimum_investment"]
    assert "1%" in by_key["exit_load"]
    assert "NIFTY 100" in by_key["benchmark"]
