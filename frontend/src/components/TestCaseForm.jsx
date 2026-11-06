import { useState } from "react";

export const QUESTION_TYPE_LABELS = {
  fact: "Sự kiện",
  multi_hop: "Ghép nhiều đoạn",
  summarization: "Tổng hợp",
  unanswerable: "Không có đáp án",
};
export const DIFFICULTY_LABELS = { easy: "Dễ", medium: "Vừa", hard: "Khó" };

function emptyReference(documents) {
  return { document_id: documents[0]?.id ?? "", quote: "" };
}

// Form thêm hoặc sửa một câu hỏi đánh giá. Câu "Không có đáp án" thì không cần đáp án chuẩn và câu trích.
export default function TestCaseForm({ documents, initial, submitLabel, onSubmit, onCancel }) {
  const [question, setQuestion] = useState(initial?.question ?? "");
  const [answer, setAnswer] = useState(initial?.ground_truth_answer ?? "");
  const [questionType, setQuestionType] = useState(initial?.question_type ?? "fact");
  const [difficulty, setDifficulty] = useState(initial?.difficulty ?? "easy");
  const [sourceNote, setSourceNote] = useState(initial?.source_note ?? "");
  const [references, setReferences] = useState(
    initial?.reference_contexts?.length
      ? initial.reference_contexts.map((ref) => ({
          document_id: documents.find((d) => d.filename === ref.filename)?.id ?? "",
          quote: ref.text,
        }))
      : [emptyReference(documents)],
  );
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const unanswerable = questionType === "unanswerable";

  function updateReference(index, field, value) {
    setReferences((current) => current.map((ref, i) => (i === index ? { ...ref, [field]: value } : ref)));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSubmit({
        question,
        ground_truth_answer: unanswerable ? null : answer,
        question_type: questionType,
        difficulty,
        expected_behavior: unanswerable ? "insufficient_context" : "answer",
        source_note: sourceNote || null,
        reference_contexts: unanswerable ? [] : references.filter((ref) => ref.document_id && ref.quote.trim()),
      });
    } catch (caught) {
      setError(caught.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card test-case-form" onSubmit={handleSubmit}>
      <label>
        Câu hỏi
        <textarea rows={2} value={question} onChange={(e) => setQuestion(e.target.value)} required />
      </label>
      <div className="form-row">
        <label>
          Loại câu hỏi
          <select value={questionType} onChange={(e) => setQuestionType(e.target.value)}>
            {Object.entries(QUESTION_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Độ khó
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            {Object.entries(DIFFICULTY_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {unanswerable ? (
        <p className="hint">Câu không có đáp án trong tài liệu: hệ thống đúng khi trả lời "không đủ thông tin".</p>
      ) : (
        <>
          <label>
            Đáp án chuẩn
            <textarea rows={2} value={answer} onChange={(e) => setAnswer(e.target.value)} required />
          </label>
          <fieldset className="references">
            <legend>Đoạn tài liệu chứa đáp án (chép nguyên văn)</legend>
            {documents.length === 0 && <p className="hint">Chưa có tài liệu nào ở trạng thái Sẵn sàng.</p>}
            {references.map((ref, index) => (
              <div key={index} className="reference-row">
                <select
                  aria-label={`Tài liệu của đoạn ${index + 1}`}
                  value={ref.document_id}
                  onChange={(e) => updateReference(index, "document_id", e.target.value)}
                >
                  {documents.map((document) => (
                    <option key={document.id} value={document.id}>
                      {document.filename}
                    </option>
                  ))}
                </select>
                <textarea
                  aria-label={`Câu trích ${index + 1}`}
                  rows={2}
                  value={ref.quote}
                  onChange={(e) => updateReference(index, "quote", e.target.value)}
                />
                {references.length > 1 && (
                  <button type="button" className="button button--ghost button--small" onClick={() => setReferences((c) => c.filter((_, i) => i !== index))}>
                    Bỏ
                  </button>
                )}
              </div>
            ))}
            <button type="button" className="button button--ghost button--small" onClick={() => setReferences((c) => [...c, emptyReference(documents)])}>
              Thêm đoạn
            </button>
          </fieldset>
        </>
      )}
      <label>
        Ghi chú nguồn (không bắt buộc)
        <input type="text" value={sourceNote} onChange={(e) => setSourceNote(e.target.value)} />
      </label>
      {error && (
        <p className="alert alert--error" role="alert">
          {error}
        </p>
      )}
      <div className="form-actions">
        <button type="submit" className="button button--primary" disabled={saving}>
          {saving ? "Đang lưu..." : submitLabel}
        </button>
        <button type="button" className="button button--ghost" onClick={onCancel}>
          Hủy
        </button>
      </div>
    </form>
  );
}
