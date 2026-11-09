// Lucian UX/UI Prompt #396 · MIT License (c) 2026 Seokwoooo · https://lucianlabs.dev/uxui-prompt/#396
import { useEffect, useRef, useState } from "react";

import "./SpoilerText.css";

// Đoạn dài (câu trả lời của LLM) có thể phủ hàng chục nghìn hạt; giới hạn để mỗi khung hình vẫn nhẹ.
const MAX_PARTICLES = 6000;

/**
 * Che một đoạn chữ bằng lớp hạt cát lấp lánh; bấm (hoặc Enter/Space) thì hạt bắn ra từ điểm bấm và chữ hiện ra,
 * "Che lại" gom hạt về che tiếp.
 *
 * Đây là che về mặt HIỂN THỊ (tránh lộ khi chia sẻ màn hình hoặc chụp báo cáo), không phải kiểm soát truy cập:
 * nội dung vẫn nằm trong DOM và trong response của API.
 */
export default function SpoilerText({ children, label = "Nội dung nhạy cảm, bấm để hiện" }) {
  const wrapRef = useRef(null);
  const textRef = useRef(null);
  const canvasRef = useRef(null);
  const engine = useRef(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    const context = canvas.getContext?.("2d");
    if (!context) return undefined;
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let width = 0;
    let height = 0;
    let particles = [];
    let visible = true;
    let frameId = 0;

    function resize() {
      width = wrap.offsetWidth;
      height = wrap.offsetHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
    }

    function boxes() {
      const origin = wrap.getBoundingClientRect();
      return [...textRef.current.getClientRects()].map((rect) => ({
        x: rect.left - origin.left,
        y: rect.top - origin.top + 2,
        w: rect.width,
        h: rect.height - 4,
      }));
    }

    function seed(scatter) {
      const areas = boxes();
      const total = areas.reduce((sum, box) => sum + (box.w * box.h) / 9, 0);
      const density = total > MAX_PARTICLES ? MAX_PARTICLES / total : 1;
      const fresh = [];
      for (const box of areas) {
        const count = Math.round(((box.w * box.h) / 9) * density);
        for (let index = 0; index < count; index += 1) {
          const x = box.x + Math.random() * box.w;
          const y = box.y + Math.random() * box.h;
          const particle = { hx: x, hy: y, x, y, vx: 0, vy: 0, a: Math.random(), r: 0.6 + Math.random() * 0.9, out: false, back: false };
          if (scatter && !reduceMotion) {
            const angle = Math.random() * Math.PI * 2;
            particle.x = x + Math.cos(angle) * 60;
            particle.y = y + Math.sin(angle) * 60;
            particle.back = true;
          }
          fresh.push(particle);
        }
      }
      return fresh;
    }

    function frame(time) {
      if (!wrap.isConnected) return;
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
      context.clearRect(0, 0, width, height);
      context.fillStyle = getComputedStyle(wrap).color;
      for (const particle of particles) {
        if (particle.out) {
          particle.x += particle.vx;
          particle.y += particle.vy;
          particle.vx *= 0.94;
          particle.vy *= 0.94;
          particle.a -= 0.025;
        } else if (particle.back) {
          particle.x += (particle.hx - particle.x) * 0.12;
          particle.y += (particle.hy - particle.y) * 0.12;
          if (Math.abs(particle.hx - particle.x) < 0.5) particle.back = false;
        } else {
          particle.x = particle.hx + Math.sin(time / 300 + particle.hy) * 0.8;
          particle.y = particle.hy + Math.cos(time / 260 + particle.hx) * 0.8;
          particle.a = 0.45 + 0.55 * Math.abs(Math.sin(time / 400 + particle.hx * 3));
        }
        if (particle.a <= 0) continue;
        context.globalAlpha = Math.max(0, Math.min(1, particle.a));
        context.fillRect(particle.x, particle.y, particle.r, particle.r);
      }
      particles = particles.filter((particle) => !particle.out || particle.a > 0);
      frameId = visible ? requestAnimationFrame(frame) : 0;
    }

    engine.current = {
      reveal(clientX, clientY) {
        const origin = wrap.getBoundingClientRect();
        const cx = clientX - origin.left;
        const cy = clientY - origin.top;
        for (const particle of particles) {
          const dx = particle.x - cx;
          const dy = particle.y - cy;
          const distance = Math.max(4, Math.hypot(dx, dy));
          particle.out = true;
          particle.vx = (dx / distance) * (2 + Math.random() * 3);
          particle.vy = (dy / distance) * (2 + Math.random() * 3) - 0.5;
          if (reduceMotion) particle.a = 0;
        }
      },
      hide() {
        resize();
        particles = particles.concat(seed(true));
      },
    };

    // Đổi kích thước (xoay màn hình, mở panel) thì xếp lại hạt theo vị trí chữ mới, chỉ khi đang che.
    const resizeObserver = new ResizeObserver(() => {
      resize();
      if (textRef.current?.dataset.open !== "true") particles = seed(false);
    });
    resizeObserver.observe(wrap);
    const intersection = new IntersectionObserver(([entry]) => {
      const was = visible;
      visible = entry.isIntersecting;
      if (visible && !was && !frameId) frameId = requestAnimationFrame(frame);
    });
    intersection.observe(wrap);

    resize();
    particles = seed(false);
    frameId = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      intersection.disconnect();
      engine.current = null;
    };
  }, []);

  function reveal(event) {
    if (open) return;
    const rect = textRef.current.getClientRects()[0] ?? textRef.current.getBoundingClientRect();
    // Bấm chuột: hạt bắn từ điểm bấm. Bàn phím (detail = 0): bắn từ giữa dòng đầu, như mẫu.
    const fromPointer = event.type === "click" && event.detail !== 0;
    const x = fromPointer ? event.clientX : rect.left + rect.width / 2;
    const y = fromPointer ? event.clientY : rect.top + rect.height / 2;
    engine.current?.reveal(x, y);
    setOpen(true);
  }

  function hide() {
    engine.current?.hide();
    setOpen(false);
  }

  return (
    <div className="spoiler">
      <div className="spoiler__body" ref={wrapRef}>
        <span
          ref={textRef}
          className={`spoiler__text${open ? " is-open" : ""}`}
          data-open={open}
          role={open ? undefined : "button"}
          tabIndex={open ? undefined : 0}
          aria-label={open ? undefined : label}
          onClick={reveal}
          onKeyDown={(event) => {
            if (!open && (event.key === "Enter" || event.key === " ")) {
              event.preventDefault();
              reveal(event);
            }
          }}
        >
          {children}
        </span>
        <canvas ref={canvasRef} className="spoiler__canvas" aria-hidden="true" />
      </div>
      {open && (
        <button type="button" className="spoiler__hide" onClick={hide}>
          Che lại
        </button>
      )}
    </div>
  );
}
