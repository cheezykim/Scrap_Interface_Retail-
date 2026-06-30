const API_URL = (import.meta.env.VITE_API_URL || "").replace(
  /\/$/,
  "",
);

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
  } catch {
    throw new Error("The scraping service is unavailable. Check that the backend is running.");
  }

  const text = await response.text().catch(() => "");
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {};
  }
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(" ")
      : data.detail;
    throw new Error(detail || text || `The request failed with status ${response.status}.`);
  }
  return data;
}

export function submitJob(payload) {
  return request("/api/jobs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getJob(jobId) {
  return request(`/api/jobs/${jobId}`);
}
