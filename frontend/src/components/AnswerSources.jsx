import { formatCost, formatLatency } from "../formatting.js";

// Phần dưới mỗi câu trả lời: nguồn được trích dẫn, mọi đoạn đã tham khảo, và số đo của lượt hỏi.
// showCitations=false khi câu trả lời đã hiện thẻ nguồn bằng CitedAnswer, để không lặp danh sách.
export default function AnswerSources({ citations = [], sources = [], metrics, showCitations = true }) {
  return (
    <div className="answer-meta">
      {showCitations && citations.length > 0 && (
        <div className="answer-citations">
          <strong>Nguồn được trích dẫn:</strong>
          <ul>
            {citations.map((citation) => (
              <li key={citation.number}>
                [{citation.number}] {citation.filename}
                {citation.page_number != null && `, trang ${citation.page_number}`}
              </li>
            ))}
          </ul>
        </div>
      )}
      {sources.length > 0 && (
        <details className="answer-sources">
          <summary>Các đoạn đã tham khảo ({sources.length})</summary>
          <ol>
            {sources.map((source) => (
              <li key={source.number}>
                <div className="answer-sources__head">
                  [{source.number}] {source.filename}
                  {source.page_number != null && `, trang ${source.page_number}`} · độ tương đồng {source.score.toFixed(3)}
                </div>
                <blockquote>{source.snippet}</blockquote>
              </li>
            ))}
          </ol>
        </details>
      )}
      {metrics && (
        <div className="answer-metrics">
          {formatLatency(metrics.latency_ms)}
          {metrics.prompt_tokens != null && ` · ${metrics.prompt_tokens} + ${metrics.completion_tokens} token`}
          {` · chi phí ước tính: ${formatCost(metrics.estimated_cost)}`}
        </div>
      )}
    </div>
  );
}
