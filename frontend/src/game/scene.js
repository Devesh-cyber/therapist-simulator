/* Quiet Room Clinic — illustrated consultation room + procedural patient character.
 * Plain JS, no dependencies. Used by the React app and inlined into the in-app artifact.
 *
 *   const scene = createScene(hostElement)
 *   scene.setPatient(look | null)        // null = empty chair
 *   scene.setEmotion("neutral" | "warm" | "sad" | "anxious" | "guarded" | "tearful" | "relieved" | "frustrated" | "thinking")
 *   scene.setTalking(bool)               // mouth animation
 *   scene.setThinking(bool)              // "…" bubble
 *   scene.setTime(progress0to1, secondsLeft)
 *   scene.enter() / scene.leave()        // patient arrival / exit animation (return Promises)
 */

export const EMOTIONS = ["neutral", "warm", "sad", "anxious", "guarded", "tearful", "relieved", "frustrated", "thinking"];

const SKIN = ["#F6D7C3", "#EDC3A0", "#D9A37C", "#B97E57", "#8E5B3D", "#5E3B26"];
const HAIR = { black: "#1F1A17", dark: "#3B2A20", brown: "#6B4A2F", auburn: "#8A4B2A", blonde: "#C9A15E", gray: "#A3A19B" };
const OUTFITS = ["#4F6D8F", "#8C5A6E", "#5D7F5F", "#B5793F", "#6A5E8C", "#3F6E73", "#9A4F45", "#56606B"];
const HAIRSTYLES = ["short", "long", "bun", "curly", "buzz", "wavy"];

function hash(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

/** Normalise an LLM- or template-provided look, filling gaps deterministically from the name. */
export function normalizeLook(look, name = "", age = 35) {
  const h = hash(name);
  const l = look || {};
  const gender = ["woman", "man", "nonbinary"].includes(l.gender) ? l.gender : (h % 2 ? "woman" : "man");
  let hair = HAIRSTYLES.includes(l.hair) ? l.hair : (gender === "woman" ? ["long", "bun", "wavy", "curly"][h % 4] : ["short", "buzz", "curly", "wavy"][h % 4]);
  let hairColor = HAIR[l.hair_color] ? l.hair_color : ["black", "dark", "brown", "auburn", "blonde", "dark"][(h >>> 3) % 6];
  if (age >= 60 && !l.hair_color) hairColor = "gray";
  const skin = Number.isInteger(l.skin) && l.skin >= 1 && l.skin <= 6 ? l.skin : 1 + ((h >>> 5) % 6);
  const outfit = /^#[0-9a-f]{6}$/i.test(l.outfit || "") ? l.outfit : OUTFITS[(h >>> 7) % OUTFITS.length];
  return {
    gender, hair, hairColor, skin, outfit,
    glasses: typeof l.glasses === "boolean" ? l.glasses : ((h >>> 9) % 4 === 0),
    beard: gender === "man" && (typeof l.beard === "boolean" ? l.beard : ((h >>> 11) % 3 === 0)),
    age,
  };
}

const ROOM = `
<svg class="qr-scene" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Consultation room">
  <defs>
    <linearGradient id="qrSky" x1="0" y1="0" x2="0" y2="1">
      <stop id="qrSkyTop" offset="0" stop-color="#BFD9E8"/><stop id="qrSkyBot" offset="1" stop-color="#F3E3C3"/>
    </linearGradient>
    <linearGradient id="qrWall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E9DCC7"/><stop offset="1" stop-color="#DDCDB4"/></linearGradient>
    <linearGradient id="qrFloor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9C7652"/><stop offset="1" stop-color="#7C5A3D"/></linearGradient>
    <linearGradient id="qrDesk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6E4A30"/><stop offset="1" stop-color="#4E331F"/></linearGradient>
    <radialGradient id="qrGlow" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFE3A8" stop-opacity=".75"/><stop offset="1" stop-color="#FFE3A8" stop-opacity="0"/></radialGradient>
    <radialGradient id="qrVignette" cx=".5" cy=".45" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#2A1A0E" stop-opacity=".35"/></radialGradient>
    <clipPath id="qrWin"><rect x="170" y="150" width="300" height="320" rx="6"/></clipPath>
  </defs>

  <!-- wall + floor -->
  <rect width="1600" height="640" fill="url(#qrWall)"/>
  <rect y="560" width="1600" height="80" fill="#CDBB9E"/>
  <rect y="556" width="1600" height="8" fill="#BFAA8A"/>
  <rect y="640" width="1600" height="260" fill="url(#qrFloor)"/>
  <g stroke="#6F5034" stroke-width="2" opacity=".35">
    <line x1="0" y1="690" x2="1600" y2="690"/><line x1="0" y1="750" x2="1600" y2="750"/><line x1="0" y1="820" x2="1600" y2="820"/>
  </g>

  <!-- window -->
  <g>
    <rect x="160" y="140" width="320" height="340" rx="10" fill="#F4ECDD"/>
    <g clip-path="url(#qrWin)">
      <rect x="170" y="150" width="300" height="320" fill="url(#qrSky)"/>
      <circle id="qrSun" cx="400" cy="230" r="34" fill="#FFF3D1" opacity=".9"/>
      <path d="M170 420 Q230 360 290 400 Q350 350 410 395 Q440 375 470 390 L470 470 L170 470Z" fill="#7E9C7C" opacity=".85"/>
      <path d="M170 445 Q250 410 330 440 Q400 420 470 440 L470 470 L170 470Z" fill="#5F7F5E"/>
      <rect id="qrDusk" x="170" y="150" width="300" height="320" fill="#1D2240" opacity="0"/>
    </g>
    <rect x="314" y="150" width="12" height="320" fill="#F4ECDD"/><rect x="170" y="300" width="300" height="12" fill="#F4ECDD"/>
    <rect x="150" y="474" width="340" height="16" rx="4" fill="#EADFCB"/>
    <path d="M130 120 Q150 300 128 500 L178 500 Q196 300 186 120Z" fill="#B65E4A"/>
    <path d="M510 120 Q490 300 512 500 L462 500 Q444 300 454 120Z" fill="#B65E4A"/>
    <rect x="110" y="108" width="420" height="14" rx="7" fill="#5A3E2B"/>
    <path d="M220 474 q-10 -40 10 -60 q8 18 0 60z M245 474 q4 -50 26 -62 q-2 30 -14 62z" fill="#6E8F5B"/>
    <rect x="212" y="466" width="56" height="12" rx="3" fill="#C27C55"/>
  </g>

  <!-- framed certificate + art -->
  <g>
    <rect x="590" y="180" width="130" height="96" rx="4" fill="#5A3E2B"/><rect x="600" y="190" width="110" height="76" fill="#FBF6EA"/>
    <rect x="618" y="204" width="74" height="6" rx="3" fill="#C9B79A"/><rect x="626" y="218" width="58" height="4" rx="2" fill="#DCCDB4"/>
    <rect x="626" y="228" width="58" height="4" rx="2" fill="#DCCDB4"/><circle cx="655" cy="250" r="8" fill="#C9714A" opacity=".7"/>
  </g>
  <g>
    <rect x="1240" y="150" width="190" height="140" rx="4" fill="#E2D3BA" stroke="#5A3E2B" stroke-width="8"/>
    <path d="M1250 270 Q1300 200 1340 240 Q1380 190 1420 250 L1420 280 L1250 280Z" fill="#8FAE9A"/>
    <circle cx="1390" cy="190" r="16" fill="#E8B76A"/>
  </g>

  <!-- wall clock (timer) -->
  <g transform="translate(1050 190)">
    <circle r="62" fill="#5A3E2B"/><circle r="54" fill="#FBF6EA"/>
    <g stroke="#5A3E2B" stroke-width="3" stroke-linecap="round">
      <line y1="-46" y2="-38"/><line y1="46" y2="38"/><line x1="-46" x2="-38"/><line x1="46" x2="38"/>
    </g>
    <path id="qrClockArc" d="" fill="#C9714A" opacity=".25"/>
    <line id="qrClockMin" y2="-38" stroke="#2A2B27" stroke-width="4" stroke-linecap="round"/>
    <line id="qrClockSec" y2="-44" stroke="#C9714A" stroke-width="2" stroke-linecap="round"/>
    <circle r="5" fill="#2A2B27"/>
  </g>

  <!-- bookshelf -->
  <g transform="translate(1250 330)">
    <rect width="210" height="330" rx="6" fill="#6B4A32"/>
    <rect x="12" y="12" width="186" height="96" fill="#4E3524"/><rect x="12" y="120" width="186" height="96" fill="#4E3524"/><rect x="12" y="228" width="186" height="90" fill="#4E3524"/>
    <g>
      <rect x="20" y="40" width="18" height="68" fill="#9A4F45"/><rect x="40" y="30" width="14" height="78" fill="#D9A63A"/><rect x="56" y="46" width="20" height="62" fill="#4F6D8F"/>
      <rect x="78" y="36" width="12" height="72" fill="#5D7F5F"/><rect x="104" y="52" width="70" height="14" fill="#C9B79A" transform="rotate(-8 104 52)"/>
      <rect x="22" y="150" width="16" height="66" fill="#3F6E73"/><rect x="40" y="140" width="22" height="76" fill="#B5793F"/><rect x="64" y="156" width="14" height="60" fill="#8C5A6E"/>
      <circle cx="150" cy="196" r="20" fill="#7E9C7C"/><rect x="138" y="196" width="24" height="20" fill="#C27C55"/>
      <rect x="22" y="262" width="60" height="56" rx="4" fill="#D8C7A8"/><rect x="100" y="250" width="16" height="68" fill="#6A5E8C"/><rect x="118" y="258" width="18" height="60" fill="#9A4F45"/>
    </g>
  </g>

  <!-- floor lamp -->
  <g>
    <circle id="qrLampGlow" cx="1520" cy="330" r="190" fill="url(#qrGlow)" opacity=".35"/>
    <rect x="1514" y="360" width="8" height="300" fill="#3A2A1E"/><ellipse cx="1518" cy="662" rx="40" ry="8" fill="#3A2A1E"/>
    <path d="M1470 360 L1566 360 L1546 290 L1490 290Z" fill="#F2DDB0"/>
  </g>

  <!-- plant -->
  <g transform="translate(520 520)">
    <path d="M40 40 Q0 -40 -30 -60 Q10 -40 30 0Z M40 40 Q60 -60 100 -90 Q70 -30 54 30Z M40 40 Q20 -20 -10 -110 Q40 -50 50 20Z M40 40 Q90 -10 120 -30 Q90 10 56 44Z" fill="#5F8A5E"/>
    <path d="M10 40 L70 40 L62 120 L18 120Z" fill="#C27C55"/><rect x="4" y="34" width="72" height="12" rx="4" fill="#A9653F"/>
  </g>

  <!-- rug -->
  <ellipse cx="800" cy="790" rx="460" ry="80" fill="#B7765A" opacity=".85"/>
  <ellipse cx="800" cy="790" rx="410" ry="62" fill="none" stroke="#E7C9A6" stroke-width="4" stroke-dasharray="14 10" opacity=".7"/>

  <!-- side table with tissues -->
  <g transform="translate(1040 560)">
    <rect x="-6" y="70" width="10" height="100" fill="#4E3524"/><rect x="86" y="70" width="10" height="100" fill="#4E3524"/>
    <rect x="-20" y="56" width="130" height="18" rx="5" fill="#6B4A32"/>
    <rect x="10" y="22" width="64" height="36" rx="5" fill="#9DB89F"/><path d="M34 22 q8 -18 16 0" fill="#FFFFFF"/>
  </g>

  <!-- armchair + patient -->
  <g id="qrChairBack">
    <path d="M650 360 Q650 300 720 296 L880 296 Q950 300 950 360 L956 640 L644 640Z" fill="#4F7A78"/>
    <path d="M672 372 Q672 326 726 322 L874 322 Q928 326 928 372 L932 560 L668 560Z" fill="#5C8A87"/>
  </g>
  <g id="qrPatient" style="opacity:0"></g>
  <g id="qrChairFront">
    <rect x="610" y="520" width="80" height="150" rx="36" fill="#446C6A"/>
    <rect x="910" y="520" width="80" height="150" rx="36" fill="#446C6A"/>
    <rect x="636" y="660" width="14" height="40" fill="#3A2A1E"/><rect x="950" y="660" width="14" height="40" fill="#3A2A1E"/>
  </g>
  <g id="qrBubble" style="opacity:0;transition:opacity .3s" transform="translate(-62 -6)">
    <path d="M880 250 q0 -40 50 -40 h70 q50 0 50 40 q0 40 -50 40 h-50 l-24 22 l4 -22 q-50 0 -50 -40z" fill="#FFFDF8" stroke="#D8CDB9" stroke-width="2"/>
    <circle class="qr-dot" cx="935" cy="250" r="7" fill="#8D8B80"/><circle class="qr-dot" cx="965" cy="250" r="7" fill="#8D8B80"/><circle class="qr-dot" cx="995" cy="250" r="7" fill="#8D8B80"/>
  </g>

  <!-- coffee table -->
  <g>
    <ellipse cx="800" cy="748" rx="250" ry="34" fill="#3A2A1E" opacity=".25"/>
    <rect x="600" y="726" width="14" height="70" fill="#4E3524"/><rect x="986" y="726" width="14" height="70" fill="#4E3524"/>
    <path d="M560 712 Q560 700 576 700 L1024 700 Q1040 700 1040 712 L1040 728 L560 728Z" fill="#7A563A"/>
    <rect x="640" y="672" width="40" height="30" rx="4" fill="#CFE3E8" opacity=".85"/><rect x="644" y="684" width="32" height="16" fill="#9CC6D2" opacity=".7"/>
    <rect x="880" y="684" width="90" height="16" rx="2" fill="#B65E4A"/><rect x="888" y="672" width="78" height="14" rx="2" fill="#4F6D8F"/>
  </g>

  <!-- the therapist's desk edge (player's side) -->
  <rect y="846" width="1600" height="60" fill="url(#qrDesk)"/>
  <rect y="840" width="1600" height="8" fill="#8A6040"/>
  <g transform="translate(1340 800)">
    <path d="M0 40 L6 0 L66 0 L72 40 Q36 52 0 40Z" fill="#F4ECDD"/><path d="M66 10 q22 0 22 14 q0 14 -20 14" fill="none" stroke="#F4ECDD" stroke-width="7"/>
    <ellipse cx="36" cy="3" rx="30" ry="5" fill="#8A5A36"/>
    <path class="qr-steam" d="M24 -8 q-8 -14 2 -26 q8 -12 -2 -26" fill="none" stroke="#FFFFFF" stroke-width="3" opacity=".55" stroke-linecap="round"/>
    <path class="qr-steam s2" d="M46 -8 q-8 -14 2 -26 q8 -12 -2 -26" fill="none" stroke="#FFFFFF" stroke-width="3" opacity=".45" stroke-linecap="round"/>
  </g>
  <rect width="1600" height="900" fill="url(#qrVignette)" pointer-events="none"/>
</svg>`;

const SCENE_CSS = `
.qr-host{position:absolute;inset:0;overflow:hidden;background:#2A1A0E}
.qr-scene{width:100%;height:100%;display:block}
#qrPatient{transition:opacity .9s ease, transform .9s ease}
.qr-breathe{animation:qrBreathe 4.2s ease-in-out infinite;transform-origin:800px 600px;transform-box:view-box}
.qr-blink{animation:qrBlink 5.2s infinite;transform-box:fill-box;transform-origin:center}
.qr-head{transition:transform .6s ease;transform-box:view-box;transform-origin:800px 410px}
.qr-dot{animation:qrDot 1.2s infinite}
.qr-dot:nth-of-type(2){animation-delay:.2s}.qr-dot:nth-of-type(3){animation-delay:.4s}
.qr-steam{animation:qrSteam 3.4s ease-in-out infinite}.qr-steam.s2{animation-delay:1.2s}
.qr-tear{animation:qrTear 2.6s ease-in infinite}
@keyframes qrBreathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.012)}}
@keyframes qrBlink{0%,94%,100%{transform:scaleY(1)}96%{transform:scaleY(.1)}}
@keyframes qrDot{0%,100%{opacity:.3}50%{opacity:1}}
@keyframes qrSteam{0%{opacity:0;transform:translateY(4px)}40%{opacity:.6}100%{opacity:0;transform:translateY(-12px)}}
@keyframes qrTear{0%{transform:translateY(0);opacity:0}20%{opacity:.9}100%{transform:translateY(26px);opacity:0}}
@media (prefers-reduced-motion:reduce){.qr-breathe,.qr-blink,.qr-dot,.qr-steam,.qr-tear{animation:none}}
`;

// ---------- character drawing ----------
function hairBack(lk, c) {
  if (lk.hair === "long") return `<path d="M744 320 Q726 420 738 470 L862 470 Q874 420 856 320Z" fill="${c}"/>`;
  if (lk.hair === "wavy" && lk.gender !== "man") return `<path d="M746 330 Q732 400 744 440 L856 440 Q868 400 854 330Z" fill="${c}"/>`;
  return "";
}
function hairFront(lk, c) {
  switch (lk.hair) {
    case "buzz": return `<path d="M752 352 Q748 296 800 292 Q852 296 848 352 Q840 318 800 314 Q760 318 752 352Z" fill="${c}" opacity=".85"/>`;
    case "short": return `<path d="M750 358 Q742 290 800 286 Q862 288 852 356 Q846 326 830 318 Q800 330 768 318 Q754 330 750 358Z" fill="${c}"/>`;
    case "bun": return `<circle cx="800" cy="284" r="24" fill="${c}"/><path d="M750 362 Q742 296 800 292 Q858 296 850 362 Q842 322 800 318 Q758 322 750 362Z" fill="${c}"/>`;
    case "curly": {
      let s = "";
      for (const [x, y, r] of [[760, 318, 20], [782, 300, 22], [808, 296, 22], [834, 304, 21], [850, 326, 18], [752, 342, 15], [852, 348, 14], [796, 314, 16], [822, 318, 15]]) s += `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;
      return s;
    }
    case "wavy": return `<path d="M748 370 Q736 292 800 288 Q866 292 852 368 Q846 330 822 320 Q790 340 760 326 Q752 340 748 370Z" fill="${c}"/>`;
    case "long":
    default: return `<path d="M748 380 Q738 290 800 286 Q862 290 852 380 Q850 332 826 318 Q800 334 774 318 Q750 332 748 380Z" fill="${c}"/>`;
  }
}

function arms(posture, o, skin) {
  const st = `fill="none" stroke="${o}" stroke-width="30" stroke-linecap="round" stroke-linejoin="round"`;
  if (posture === "crossed") {
    return `<path d="M730 440 Q716 490 748 506 L842 498" ${st}/><path d="M870 440 Q884 490 852 512 L760 512" ${st}/>
      <circle cx="846" cy="497" r="13" fill="${skin}"/><circle cx="756" cy="512" r="13" fill="${skin}"/>`;
  }
  if (posture === "clasped") {
    return `<path d="M730 440 Q706 520 790 568" ${st}/><path d="M870 440 Q894 520 810 568" ${st}/>
      <ellipse cx="800" cy="570" rx="22" ry="15" fill="${skin}"/>`;
  }
  if (posture === "face") { // hand near face — tearful/sad
    return `<path d="M730 440 Q712 520 772 570" ${st}/><path d="M870 440 Q900 470 874 432 L848 404" ${st}/>
      <circle cx="776" cy="572" r="14" fill="${skin}"/><circle cx="842" cy="398" r="14" fill="${skin}"/>`;
  }
  return `<path d="M730 440 Q708 520 762 574" ${st}/><path d="M870 440 Q892 520 838 574" ${st}/>
    <circle cx="764" cy="577" r="14" fill="${skin}"/><circle cx="836" cy="577" r="14" fill="${skin}"/>`;
}

const FACE = {
  neutral:   { brows: ["M772 336 Q782 332 792 335", "M808 335 Q818 332 828 336"], mouth: "M788 392 Q800 396 812 392", gaze: [0, 0], tilt: 0, posture: "lap" },
  warm:      { brows: ["M772 334 Q782 328 792 333", "M808 333 Q818 328 828 334"], mouth: "M784 389 Q800 403 816 389", gaze: [0, 0], tilt: -2, posture: "lap" },
  relieved:  { brows: ["M772 336 Q782 330 792 334", "M808 334 Q818 330 828 336"], mouth: "M786 390 Q800 400 814 390", gaze: [0, 1], tilt: 3, posture: "lap", closed: true },
  sad:       { brows: ["M772 338 Q784 336 792 330", "M808 330 Q816 336 828 338"], mouth: "M788 397 Q800 390 812 397", gaze: [0, 4], tilt: 6, posture: "clasped" },
  tearful:   { brows: ["M772 339 Q784 336 792 329", "M808 329 Q816 336 828 339"], mouth: "M789 398 Q800 389 811 398", gaze: [0, 4], tilt: 7, posture: "face", tear: true },
  anxious:   { brows: ["M772 333 Q782 328 792 331", "M808 331 Q818 328 828 333"], mouth: "M789 393 Q795 390 800 393 Q805 396 811 393", gaze: [-3, 0], tilt: -1, posture: "clasped" },
  guarded:   { brows: ["M772 339 Q782 337 792 340", "M808 340 Q818 337 828 339"], mouth: "M790 394 L810 394", gaze: [5, 1], tilt: -4, posture: "crossed" },
  frustrated:{ brows: ["M772 334 Q784 338 792 342", "M808 342 Q816 338 828 334"], mouth: "M789 396 Q800 391 811 396", gaze: [0, 0], tilt: 0, posture: "crossed" },
  thinking:  { brows: ["M772 334 Q782 330 792 334", "M808 331 Q818 326 828 331"], mouth: "M791 393 Q800 394 809 392", gaze: [4, -4], tilt: -3, posture: "lap" },
};

function characterSVG(lk, emotion) {
  const f = FACE[emotion] || FACE.neutral;
  const skin = SKIN[lk.skin - 1];
  const hc = HAIR[lk.hairColor] || HAIR.dark;
  const o = lk.outfit;
  const pants = "#3A3A40";
  const [gx, gy] = f.gaze;
  const eye = (x) => f.closed
    ? `<path d="M${x - 6} 360 Q${x} 364 ${x + 6} 360" stroke="#2A2220" stroke-width="3" fill="none" stroke-linecap="round"/>`
    : `<ellipse class="qr-blink" cx="${x + gx}" cy="${358 + gy}" rx="5" ry="6.5" fill="#2A2220"/>`;
  return `
  <g class="qr-breathe">
    <rect x="712" y="600" width="44" height="160" rx="18" fill="${pants}"/><rect x="844" y="600" width="44" height="160" rx="18" fill="${pants}"/>
    <ellipse cx="732" cy="764" rx="30" ry="12" fill="#2B2420"/><ellipse cx="868" cy="764" rx="30" ry="12" fill="#2B2420"/>
    <rect x="708" y="560" width="184" height="60" rx="26" fill="${pants}"/>
    <g class="qr-head" style="transform:rotate(${f.tilt}deg)">${hairBack(lk, hc)}</g>
    <path d="M722 448 Q720 420 752 414 L848 414 Q880 420 878 448 L886 590 L714 590Z" fill="${o}"/>
    <path d="M776 414 L800 444 L824 414Z" fill="${skin}"/>
    <path d="M770 414 L800 450 L830 414" fill="none" stroke="#000" stroke-opacity=".15" stroke-width="3"/>
    ${arms(f.posture, o, skin)}
    <g class="qr-head" style="transform:rotate(${f.tilt}deg) translateY(${f.tilt > 4 ? 4 : 0}px)">
      <rect x="786" y="392" width="28" height="30" rx="8" fill="${skin}"/>
      <ellipse cx="752" cy="362" rx="9" ry="13" fill="${skin}"/><ellipse cx="848" cy="362" rx="9" ry="13" fill="${skin}"/>
      <ellipse cx="800" cy="352" rx="49" ry="57" fill="${skin}"/>
      ${lk.beard ? `<path d="M754 364 Q760 414 800 418 Q840 414 846 364 Q840 396 800 402 Q760 396 754 364Z" fill="${hc}" opacity=".85"/>` : ""}
      <ellipse cx="772" cy="378" rx="9" ry="5" fill="#E58F7A" opacity=".22"/><ellipse cx="828" cy="378" rx="9" ry="5" fill="#E58F7A" opacity=".22"/>
      ${eye(782)}${eye(818)}
      <path d="${f.brows[0]}" stroke="${hc}" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="${f.brows[1]}" stroke="${hc}" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="M800 362 Q796 374 801 377" stroke="#000" stroke-opacity=".22" stroke-width="2.5" fill="none" stroke-linecap="round"/>
      <path class="qr-mouth" d="${f.mouth}" stroke="#7A3E33" stroke-width="3.5" fill="none" stroke-linecap="round"/>
      <ellipse class="qr-mouth-open" cx="800" cy="393" rx="7" ry="5" fill="#7A3E33" opacity="0"/>
      ${f.tear ? `<path class="qr-tear" d="M776 368 q-4 8 0 12 q4 -4 0 -12z" fill="#8FC3E0"/>` : ""}
      ${lk.glasses ? `<g fill="none" stroke="#2A2B27" stroke-width="3"><rect x="766" y="346" width="30" height="24" rx="8"/><rect x="804" y="346" width="30" height="24" rx="8"/><path d="M796 356 h8"/></g>` : ""}
      ${hairFront(lk, hc)}
    </g>
  </g>`;
}

function lerp(a, b, t) { return a + (b - a) * t; }
function mix(c1, c2, t) {
  const p = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [a, b] = [p(c1), p(c2)];
  return "#" + a.map((v, i) => Math.round(lerp(v, b[i], t)).toString(16).padStart(2, "0")).join("");
}

export function createScene(host) {
  if (!document.getElementById("qr-scene-css")) {
    const st = document.createElement("style"); st.id = "qr-scene-css"; st.textContent = SCENE_CSS; document.head.appendChild(st);
  }
  host.classList.add("qr-host");
  host.innerHTML = ROOM;
  const $ = (id) => host.querySelector("#" + id);
  const patient = $("qrPatient");
  let look = null, emotion = "neutral", talkTimer = null;

  const draw = () => { if (look) patient.innerHTML = characterSVG(look, emotion); };

  const api = {
    setPatient(l) { look = l; if (!l) { patient.innerHTML = ""; patient.style.opacity = "0"; } else draw(); },
    setEmotion(e) { const next = FACE[e] ? e : "neutral"; if (next !== emotion) { emotion = next; draw(); } },
    getEmotion() { return emotion; },
    setThinking(on) { $("qrBubble").style.opacity = on ? "1" : "0"; if (on) api.setEmotion("thinking"); },
    setTalking(on) {
      clearInterval(talkTimer);
      const open = () => patient.querySelector(".qr-mouth-open"), line = () => patient.querySelector(".qr-mouth");
      if (!on) { if (open()) { open().setAttribute("opacity", "0"); line().setAttribute("opacity", "1"); } return; }
      let o = false;
      talkTimer = setInterval(() => {
        o = !o;
        if (open()) { open().setAttribute("opacity", o ? "1" : "0"); line().setAttribute("opacity", o ? "0" : "1"); }
      }, 130);
    },
    setTime(progress, secondsLeft) {
      const t = Math.max(0, Math.min(1, progress));
      $("qrSkyTop").setAttribute("stop-color", mix("#BFD9E8", "#4A4F86", t));
      $("qrSkyBot").setAttribute("stop-color", mix("#F3E3C3", "#E8996A", t));
      $("qrDusk").setAttribute("opacity", String(t * 0.35));
      $("qrSun").setAttribute("cy", String(lerp(230, 430, t)));
      $("qrSun").setAttribute("fill", mix("#FFF3D1", "#FFB27A", t));
      $("qrLampGlow").setAttribute("opacity", String(0.3 + t * 0.6));
      const s = Math.max(0, secondsLeft ?? 0);
      const minAngle = (s / 600) * 360, secAngle = ((s % 60) / 60) * 360;
      $("qrClockMin").setAttribute("transform", `rotate(${minAngle})`);
      $("qrClockSec").setAttribute("transform", `rotate(${secAngle})`);
      const a = (minAngle - 90) * Math.PI / 180, large = minAngle > 180 ? 1 : 0;
      $("qrClockArc").setAttribute("d", s > 0 ? `M0 0 L0 -50 A50 50 0 ${large} 1 ${50 * Math.cos(a)} ${50 * Math.sin(a)} Z` : "");
    },
    enter() {
      return new Promise((res) => {
        patient.style.transform = "translateY(14px)"; patient.style.opacity = "0";
        requestAnimationFrame(() => requestAnimationFrame(() => { patient.style.transform = "translateY(0)"; patient.style.opacity = "1"; }));
        setTimeout(res, 950);
      });
    },
    leave() {
      return new Promise((res) => {
        patient.style.transform = "translateY(10px)"; patient.style.opacity = "0"; setTimeout(res, 950);
      });
    },
    show() { patient.style.opacity = "1"; patient.style.transform = "none"; },
  };
  api.setTime(0, 600);
  return api;
}
