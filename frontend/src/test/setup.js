import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom không có canvas; component vẽ bằng canvas (SpoilerText) tự bỏ qua phần vẽ khi getContext trả về null.
HTMLCanvasElement.prototype.getContext = () => null;

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});
