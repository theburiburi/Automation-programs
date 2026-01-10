let timeOffset = null;
let timer = null;

// 서버시간 동기화
async function syncServerTime() {
  const start = Date.now();

  const res = await fetch("https://www.naver.com", {
    method: "HEAD",
    cache: "no-store"
  });

  const end = Date.now();
  const dateHeader = res.headers.get("Date");

  const serverTime = new Date(dateHeader).getTime();
  const latency = (end - start) / 2;

  timeOffset = serverTime + latency - end;
}

// 서버 기준 현재 시간
function getServerNow() {
  if (timeOffset === null) return null;
  return Date.now() + timeOffset;
}

document.addEventListener("DOMContentLoaded", async () => {
  const serverTimeEl = document.getElementById("serverTime");
  const reserveBtn = document.getElementById("reserveBtn");
  const statusEl = document.getElementById("status");

  const hourInput = document.getElementById("hour");
  const minuteInput = document.getElementById("minute");
  const secondInput = document.getElementById("second");

  // 서버시간 표시
  setInterval(() => {
    const now = getServerNow();
    if (!now) return;

    serverTimeEl.textContent = new Date(now).toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23"
    });
  }, 100);

  await syncServerTime();

  reserveBtn.addEventListener("click", () => {
    const h = Number(hourInput.value);
    const m = Number(minuteInput.value);
    const s = Number(secondInput.value || 0);

    if (
      h < 0 || h > 23 ||
      m < 0 || m > 59 ||
      s < 0 || s > 59
    ) {
      statusEl.textContent = "시간 입력 오류";
      return;
    }

    const now = getServerNow();
    const target = new Date(now);
    target.setHours(h, m, s, 0);

    if (target <= now) {
      target.setDate(target.getDate() + 1);
    }

    statusEl.textContent =
      "예약 활성화됨 (" +
      target.toLocaleTimeString("ko-KR", { hourCycle: "h23" }) +
      ")";

    if (timer) clearInterval(timer);

    timer = setInterval(() => {
      if (getServerNow() >= target.getTime()) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs[0]) {
            chrome.tabs.reload(tabs[0].id);
          }
        });
        clearInterval(timer);
      }
    }, 50);
  });
});
