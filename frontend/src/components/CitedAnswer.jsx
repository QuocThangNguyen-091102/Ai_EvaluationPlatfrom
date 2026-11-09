// Lucian UX/UI Prompt #224 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#224
import { Fragment, useRef, useState } from "react";

import "./CitedAnswer.css";

const MARKER_GROUP = /((?:\[\d+\])+)/;
const COLORS = ["#6366F1", "#F59E0B", "#10B981"];
const PREVIEW_HALF_WIDTH = 150;
const SHOW_BELOW_WHEN_TOP_UNDER = 150;

function describePage(source) {
  return source.page_number != null ? `trang ${source.page_number}` : "không rõ trang";
}

// Câu trả lời ghi nguồn sau mỗi ý dạng [1] hoặc [1][3] (prompt rag-grounded-citations). Mỗi ý là đoạn chữ đứng
// trước một nhóm số nguồn. Số không khớp với đoạn nào đã đưa cho LLM thì giữ nguyên dạng chữ, không biến thành nút.
function splitClaims(text, known) {
  const parts = text.split(MARKER_GROUP);
  const claims = [];
  for (let index = 0; index < parts.length; index += 2) {
    const group = parts[index + 1] ?? "";
    const numbers = [...group.matchAll(/\[(\d+)\]/g)].map((match) => Number(match[1]));
    // Dấu câu đứng sau nhóm số nguồn (". ", ", ") thuộc về ý trước, không gạch chân như đầu ý sau.
    const [, lead = "", body = ""] = parts[index].match(/^([\s.,;:!?…)\]]*)([\s\S]*)$/) ?? [];
    claims.push({
      lead,
      text: body,
      numbers: numbers.filter((number) => known.has(number)),
      unknown: numbers.filter((number) => !known.has(number)),
    });
  }
  return claims;
}

/**
 * Câu trả lời có thể lần ngược về nguồn. Trỏ vào một số nguồn: ý đó được gạch chân, thẻ xem trước hiện đoạn trích
 * và thẻ nguồn bên dưới nhấc lên. Trỏ vào một thẻ nguồn: mọi ý dùng nguồn đó được đánh dấu cùng lúc.
 *
 * Khác mẫu: mẫu tô vàng đúng cụm từ được trích, nhưng hệ thống chỉ biết ý dựa vào ĐOẠN nào, không biết cụm từ nào,
 * nên thẻ xem trước hiện nguyên đoạn trích thay vì đánh dấu một cụm đoán ra.
 */
export default function CitedAnswer({ text, sources = [], citations = [] }) {
  const rootRef = useRef(null);
  const [active, setActive] = useState(null);

  const byNumber = new Map([...sources, ...citations].map((source) => [source.number, source]));
  const claims = splitClaims(text, byNumber);
  const cited = citations.length > 0 ? citations : [...new Set(claims.flatMap((claim) => claim.numbers))].map((number) => byNumber.get(number));
  const colorOf = (number) => COLORS[(number - 1) % COLORS.length];

  function showCitation(event, claimIndex, number) {
    const root = rootRef.current.getBoundingClientRect();
    const button = event.currentTarget.getBoundingClientRect();
    const top = button.top - root.top;
    const center = button.left + button.width / 2 - root.left;
    const half = Math.min(PREVIEW_HALF_WIDTH, root.width / 2);
    setActive({
      kind: "citation",
      claimIndex,
      number,
      left: Math.max(half, Math.min(root.width - half, center)),
      top,
      below: top < SHOW_BELOW_WHEN_TOP_UNDER,
    });
  }

  const clear = () => setActive(null);
  const claimLit = (claim, index) =>
    active?.kind === "citation" ? active.claimIndex === index : active?.kind === "source" && claim.numbers.includes(active.number);
  const citeLit = (index, number) =>
    active?.kind === "citation" ? active.claimIndex === index && active.number === number : active?.number === number;
  const previewSource = active?.kind === "citation" ? byNumber.get(active.number) : null;

  return (
    <div className="cited-answer" ref={rootRef}>
      <p className="cited-answer__text">
        {claims.map((claim, index) => (
          <Fragment key={index}>
            {claim.lead}
            <span className={claimLit(claim, index) ? "is-hl" : undefined}>{claim.text}</span>
            {claim.numbers.map((number) => {
              const source = byNumber.get(number);
              return (
                <button
                  key={number}
                  type="button"
                  className={`cited-answer__cite${citeLit(index, number) ? " is-on" : ""}`}
                  aria-label={`Nguồn ${number}: ${source.filename}, ${describePage(source)}`}
                  onPointerEnter={(event) => showCitation(event, index, number)}
                  onFocus={(event) => showCitation(event, index, number)}
                  onPointerLeave={clear}
                  onBlur={clear}
                >
                  {number}
                </button>
              );
            })}
            {claim.unknown.map((number) => `[${number}]`).join("")}
          </Fragment>
        ))}
      </p>

      <div
        className={`cited-answer__preview${previewSource ? " is-on" : ""}${active?.below ? " is-below" : ""}`}
        style={active?.kind === "citation" ? { left: `${active.left}px`, top: `${active.top}px` } : undefined}
        role="tooltip"
        aria-hidden={!previewSource}
      >
        {previewSource && (
          <>
            <header>
              <i style={{ background: colorOf(previewSource.number) }}>{previewSource.number}</i>
              <span>
                {previewSource.filename} · {describePage(previewSource)}
              </span>
            </header>
            <b>Đoạn đã đưa cho LLM</b>
            <p>{previewSource.snippet}</p>
          </>
        )}
      </div>

      {cited.length > 0 && (
        <div className="cited-answer__sources">
          <small>Nguồn được trích dẫn</small>
          <div className="cited-answer__list">
            {cited.map((source) => (
              <div
                key={source.number}
                className={`cited-answer__card${active?.number === source.number ? " is-on" : ""}`}
                tabIndex={0}
                aria-label={`Nguồn ${source.number}: ${source.filename}, ${describePage(source)}. Đánh dấu các ý dùng nguồn này.`}
                onPointerEnter={() => setActive({ kind: "source", number: source.number })}
                onFocus={() => setActive({ kind: "source", number: source.number })}
                onPointerLeave={clear}
                onBlur={clear}
              >
                <header>
                  <i style={{ background: colorOf(source.number) }}>{source.filename[0]?.toUpperCase()}</i>
                  <em>{source.number}</em>
                </header>
                <b>{source.filename}</b>
                <small>{describePage(source)}</small>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
