# Cluster overview

Start the monitoring API and open `/ui/` on the same origin. No package install, frontend build, or CDN is required. The viewer requests eight fixed `GET /rest/1.0/dashboard/*` endpoints on load and on **Refresh**. It does not poll, modify resources, or store responses. An unavailable request is different from a reported zero. “Checked” is the browser request time, not a metric sample timestamp.

Run the offline checks from the repository root with Node.js 18 or newer:

```sh
node --test ui/dashboard.test.mjs
```
