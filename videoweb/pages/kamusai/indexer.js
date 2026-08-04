// KamusAI Segment Indexer — maps global time/frames to segment index & local time
const FPS = 24;

export const SEGMENTS = [
  { num: 1, name: 'SEGMENT_1', secStart: 0.0,  secEnd: 8.0,   duration: 8.0 },
  { num: 2, name: 'SEGMENT_2', secStart: 8.0,  secEnd: 26.0,  duration: 18.0 },
  { num: 3, name: 'SEGMENT_3', secStart: 26.0, secEnd: 52.0,  duration: 26.0 },
  { num: 4, name: 'SEGMENT_4', secStart: 52.0, secEnd: 61.5,  duration: 9.5 },
];

export const TOTAL_DURATION = 61.5;
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
  if (parts[0] === 'kamusai' && parts.length >= 2) {
    return parseInt(parts[1], 10);
  }
  return null;
}
