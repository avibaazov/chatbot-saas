"use client";

import { useEffect } from "react";

/**
 * Loads the real embeddable widget onto this page — same `<script>` tag a customer pastes
 * on their own site — so the dashboard shows the live bubble in the bottom-right corner,
 * exactly like the demo sites. Renders nothing itself; the widget appends its own
 * fixed-position host to <body> and cleans it up on navigation away.
 */
export function WidgetMount({
  siteKey,
  apiBase,
  scriptUrl,
  offsetBottom = 0,
  reloadKey,
}: {
  siteKey: string;
  apiBase: string;
  scriptUrl: string;
  offsetBottom?: number;
  // Change this to force the widget to re-mount — e.g. after saving appearance, so the
  // new colour/font/name show without a manual page reload.
  reloadKey?: string;
}) {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = scriptUrl;
    script.async = true;
    script.dataset.botKey = siteKey;
    script.dataset.apiBase = apiBase;
    if (offsetBottom > 0) script.dataset.offsetBottom = String(offsetBottom);
    document.body.appendChild(script);

    return () => {
      script.remove();
      document
        .querySelectorAll("[data-chatbot-widget]")
        .forEach((el) => el.remove());
    };
  }, [siteKey, apiBase, scriptUrl, offsetBottom, reloadKey]);

  return null;
}
