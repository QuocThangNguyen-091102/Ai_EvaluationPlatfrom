import { useEffect, useRef } from "react";

import { useToast } from "./useToast.js";

/**
 * Phát toast khi một mục (lượt chạy, tài liệu) chuyển từ trạng thái chưa xong sang đã xong trong lúc trang đang polling.
 *
 * Lần nhận dữ liệu đầu tiên chỉ ghi nhận, không thông báo, để mở trang không bắn toast cho những mục đã xong từ trước.
 * `describe(item)` trả về { tone, title, detail } cho trạng thái cuối của mục, hoặc null nếu không cần thông báo.
 */
export function useRunNotifications(items, { isUnfinished, describe }) {
  const { notify } = useToast();
  const previous = useRef(null);

  useEffect(() => {
    if (!items) return;
    const statuses = new Map(items.map((item) => [item.id, item.status]));
    if (previous.current !== null) {
      for (const item of items) {
        const before = previous.current.get(item.id);
        if (before && isUnfinished(before) && !isUnfinished(item.status)) {
          const message = describe(item);
          if (message) notify(message);
        }
      }
    }
    previous.current = statuses;
  }, [items, isUnfinished, describe, notify]);
}
