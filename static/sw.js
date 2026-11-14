/* Service Worker de ApuestaEdge para alertas Web Push. */
"use strict";

self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { title: "ApuestaEdge", body: event.data ? event.data.text() : "" };
  }
  const title = payload.title || "ApuestaEdge · Nueva alerta de valor";
  const options = {
    body: payload.body || "Revisa tu bandeja de alertas en /alertas.",
    tag: payload.tag || "apuestaedge-alert",
    data: { url: payload.url || "/alertas" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("message", (event) => {
  const msg = event.data || {};
  if (msg.type === "SHOW_ALERT") {
    const title = msg.title || "ApuestaEdge · Alerta de valor";
    const options = {
      body: msg.body || "",
      tag: msg.tag || "apuestaedge-alert",
      data: { url: msg.url || "/alertas" },
    };
    event.waitUntil(self.registration.showNotification(title, options));
  }
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = (event.notification.data && event.notification.data.url) || "/alertas";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ("focus" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }
      return null;
    })
  );
});
