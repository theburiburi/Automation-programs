/**
 * 서버 시간 가져오기 (초 잘림 보정 포함)
 */
async function getServerTime() {
  const t0 = Date.now();

  const res = await fetch("https://www.naver.com", {
    method: "HEAD",
    cache: "no-store",
  });

  const t1 = Date.now();
  const dateHeader = res.headers.get("Date");

  // 서버에서 내려준 초 단위 시간
  const serverBase = new Date(dateHeader).getTime();

  // RTT 보정
  const latency = (t1 - t0) / 2;

  /**
   * 🔥 중요
   * Date 헤더는 초 시작값이므로
   * 실제 서버 시간에 근접시키기 위해 +1000ms 보정
   */
  const correctedServerTime = serverBase + latency + 1000;

  return {
    serverTime: correctedServerTime,
    localTime: t1
  };
}

/**
 * 메시지 처리
 */
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  // 서버 시간 요청 (표시용)
  if (msg.type === "GET_SERVER_TIME") {
    getServerTime().then(({ serverTime }) => {
      sendResponse({ serverTime });
    });
    return true;
  }

  // 새로고침 예약
  if (msg.type === "RESERVE_REFRESH") {
    (async () => {
      const { serverTime, localTime } = await getServerTime();
      const offset = serverTime - localTime;

      const [h, m, s] = msg.targetTime.split(":").map(Number);

      const targetServer = new Date(serverTime);
      targetServer.setHours(h, m, s, 0);

      if (targetServer.getTime() <= serverTime) {
        targetServer.setDate(targetServer.getDate() + 1);
      }

      // 알람은 로컬 기준
      const alarmTime = targetServer.getTime() - offset;

      await chrome.storage.local.set({
        reservation: {
          tabId: msg.tabId,
          targetServerTime: targetServer.getTime(),
          alarmTime
        }
      });

      chrome.alarms.create("REFRESH_ALARM", {
        when: alarmTime
      });

      console.log("⏰ 서버 기준 예약:", new Date(targetServer).toISOString());
    })();
  }
});

/**
 * 알람 트리거
 */
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "REFRESH_ALARM") return;

  const { reservation } = await chrome.storage.local.get("reservation");
  if (!reservation) return;

  chrome.tabs.reload(reservation.tabId);
  await chrome.storage.local.remove("reservation");

  console.log("🔄 새로고침 실행");
});
