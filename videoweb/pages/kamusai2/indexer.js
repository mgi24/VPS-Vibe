// KamusAI2 Segment Indexer — maps global time/frames to segment index & local time
const FPS = 24;

export const SEGMENTS = [
  { num: 1, name: 'INTRO',   secStart: 0.0,  secEnd: 3.6,    duration: 3.6 },
  { num: 2, name: 'LLM',     secStart: 3.6,  secEnd: 11.4,   duration: 7.8 },
  { num: 3, name: 'MULTIMODAL', secStart: 11.4, secEnd: 27.06, duration: 15.66 },
  { num: 4, name: 'INPUT',   secStart: 27.06,secEnd: 40.4,   duration: 13.34 },
  { num: 5, name: 'THINKING',secStart: 40.4, secEnd: 52.7,   duration: 12.3 },
  { num: 6, name: 'THINKING_OFF',secStart: 52.7,secEnd: 59.8, duration: 7.1 },
  { num: 7, name: 'OUTRO',   secStart: 59.7, secEnd: 63.2,   duration: 3.4 },
];

export const TOTAL_DURATION = 63.2;
export const TOTAL_FRAMES = Math.round(TOTAL_DURATION * FPS);

export function getTimeInfo(globalSec) {
  for (const seg of SEGMENTS) {
    if (globalSec >= seg.secStart && globalSec < seg.secEnd) {
      const localTime = globalSec - seg.secStart;
      return { segmentNum: seg.num, localTime, secStart: seg.secStart };
    }
  }
  const lastSeg = SEGMENTS[SEGMENTS.length - 1];
  return { segmentNum: lastSeg.num, localTime: lastSeg.duration, secStart: lastSeg.secStart };
}

export function getFrameInfo(globalFrame) {
  const globalSec = globalFrame / FPS;
  const info = getTimeInfo(globalSec);
  const localFrame = Math.round(info.localTime * FPS);
  return { ...info, localFrame };
}

export function getSegmentRange(segmentNum) {
  return SEGMENTS[segmentNum - 1];
}

export function isActiveAt(globalSec, segmentNum) {
  const seg = SEGMENTS.find(s => s.num === segmentNum);
  if (!seg) return false;
  return globalSec >= seg.secStart && globalSec < seg.secEnd;
}

export function getVisibleSegments(globalSec) {
  return SEGMENTS.filter(seg => {
    const margin = 0.3;
    return globalSec >= seg.secStart - margin && globalSec < seg.secEnd + margin;
  });
}

export function getSegmentFromPath(pathname) {
  const parts = pathname.replace(/^\/+|\/+$/g, '').split('/');
  if (parts[0] === 'kamusai2' && parts.length >= 2) {
    return parseInt(parts[1], 10);
  }
  return null;
}
