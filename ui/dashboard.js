const inventory = [
  ['nodes', 'Nodes', 'ready_nodes', 'total_nodes', 'ready / total'],
  ['namespaces', 'Namespaces', null, 'total_namespaces', 'active namespaces'],
  ['pods', 'Pods', 'running_pods', 'total_pods', 'running / total'],
  ['workloads', 'Workloads', 'ready_workloads', 'total_workloads', 'ready / total'],
  ['services', 'Services', 'endpoints_services', 'total_services', 'healthy / total'],
];
const utilization = [
  ['resource_usage', 'Cluster', [['CPU','cpu_usage'], ['Memory','memory_usage'], ['Disk','disk_usage']]],
  ['gpu_usage', 'GPU', [['Compute','Compute'], ['Memory copy','Memory'], ['Encode','Encode'], ['Decode','Decode']]],
];
const format = new Intl.NumberFormat(undefined, {maximumFractionDigits: 2});
export const endpoints = [...inventory.map(r => r[0]), ...utilization.map(r => r[0]), 'events'];

export function metric(value, suffix = '') {
  if (typeof value !== 'number' && (typeof value !== 'string' || !value.trim())) return 'N/A';
  const n = Number(value);
  return Number.isFinite(n) ? format.format(n) + suffix : 'N/A';
}

export async function load(name, request = fetch) {
  if (!endpoints.includes(name)) throw Error('Unknown panel');
  const response = await request(`/rest/1.0/dashboard/${name}`, {
    method: 'GET', credentials: 'same-origin', mode: 'same-origin', redirect: 'error', cache: 'no-store',
    signal: AbortSignal.timeout(15000), headers: {Accept: 'application/json'},
  });
  if (!response.ok) throw Error(`HTTP ${response.status}`);
  const data = await response.json();
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error('Invalid response');
  return data;
}

function element(tag, text, css) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (css) el.className = css;
  return el;
}

function panel(title) {
  const el = element('article');
  el.append(element('h3', title));
  return el;
}

function message(el) {
  el.append(element('p', 'Unavailable', 'issue'));
}

function buildEvents(el, data) {
  if (!Array.isArray(data.events)) return message(el);
  el.append(element('p', `${metric(data.normal_events)} normal · ${metric(data.warning_events)} warning`));
  if (!data.events.length) {el.append(element('p', 'No events returned.', 'sub')); return;}
  const wrap = element('div', undefined, 'table-wrap');
  const table = element('table');
  table.append(element('caption', 'Up to 20 recent events'));
  const fields = [['Last seen','last_seen'], ['Type','type'], ['Namespace','namespace'], ['Object','object'], ['Reason','reason']];
  const row = table.createTHead().insertRow();
  for (const [label] of fields) {const th = element('th', label); th.scope = 'col'; row.append(th);}
  const body = table.createTBody();
  for (const item of data.events.slice(0,20)) {
    const tr = body.insertRow();
    for (const [,key] of fields) tr.append(element('td', typeof item?.[key] === 'string' ? item[key] : 'N/A'));
  }
  wrap.append(table); el.append(wrap);
}

async function refresh() {
  const get = id => document.getElementById(id);
  const button = get('refresh');
  if (button.disabled) return;
  button.disabled = true;
  get('status').textContent = 'Refreshing…';
  try {
    const results = await Promise.allSettled(endpoints.map(name => load(name)));
    const data = Object.fromEntries(endpoints.map((key,i) => [key, results[i].value]));
    get('inventory').replaceChildren(...inventory.map(([key,title,part,total,label]) => {
      const el = panel(title), item = data[key];
      if (item) {
        el.append(element('p', (part ? `${metric(item[part])} / ` : '') + metric(item[total]), 'value'), element('p', label, 'sub'));
      } else message(el);
      return el;
    }));
    get('metrics').replaceChildren(...utilization.map(([key,title,fields]) => {
      const el = panel(title); el.classList.add('metrics');
      if (data[key]) for (const [label,field] of fields) {
        const row = element('div'); row.append(element('span', label), element('strong', metric(data[key][field], '%'))); el.append(row);
      } else message(el);
      return el;
    }));
    const events = get('events'); events.replaceChildren();
    if (data.events) buildEvents(events, data.events); else message(events);
    const unavailable = results.filter(r => r.status === 'rejected').length;
    get('status').textContent = `Checked ${new Date().toLocaleTimeString()} · ${unavailable ? `${unavailable} of ${results.length} requests failed` : 'All requests completed'}`;
  } finally {button.disabled = false;}
}

if (typeof document !== 'undefined') {
  document.getElementById('refresh').addEventListener('click', refresh);
  refresh();
}
