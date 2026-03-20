<script lang="ts">
  import { Motion } from 'svelte-motion';
  import type { User } from '$lib/services/users';

  export let user: User;

  $: fullName  = `${user.nome ?? ''} ${user.cognome ?? ''}`.trim();
  $: initials  = `${user.nome?.[0] ?? ''}${user.cognome?.[0] ?? ''}`.toUpperCase();
  $: roleLabel = user.contratti?.find((c) => c.is_active)?.tipologia ?? 'Dipendente';

  let rotateX = 0, rotateY = 0;
  let glowX = 50, glowY = 50;
  let isHover = false;

  function onMouseMove(e: MouseEvent) {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const dx = (e.clientX - r.left) / r.width;
    const dy = (e.clientY - r.top)  / r.height;
    rotateY =  (dx - 0.5) * 12;
    rotateX = -(dy - 0.5) * 12;
    glowX   = dx * 100;
    glowY   = dy * 100;
  }

  function onEnter() { isHover = true; }
  function onLeave() {
    isHover = false;
    rotateX = rotateY = 0;
    glowX = glowY = 50;
  }

  const fmtSaldo = (n: unknown) =>
    `${new Intl.NumberFormat('it-IT', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number(n) || 0)} h`;

  function openMail() {
    const email = user?.email?.trim();
    if (!email) return;
    window.location.href = `mailto:${email}`;
  }
</script>

<div style="perspective: 900px;" class="w-full">
  <Motion
    initial={{ opacity: 0, y: 32, scale: 0.94 }}
    animate={{ opacity: 1, y: 0,  scale: 1    }}
    transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
    let:motion
  >
    <div
      use:motion
      style="
        transform: rotateX({rotateX}deg) rotateY({rotateY}deg);
        transition: transform {isHover ? '0.07s' : '0.5s'} cubic-bezier(0.22,1,0.36,1);
        transform-style: preserve-3d;
        will-change: transform;
      "
      on:mousemove={onMouseMove}
      on:mouseenter={onEnter}
      on:mouseleave={onLeave}
      role="article"
      aria-label="Profilo di {fullName}"
    >

      <!-- ╔══ CARD — sfondo bianco ══════════════════════════╗ -->
      <div class="
        relative w-full rounded-2xl overflow-visible
        bg-white border border-orange-100
        shadow-[0_4px_6px_-1px_rgba(249,115,22,.08),0_20px_50px_-8px_rgba(249,115,22,.15),0_2px_4px_rgba(0,0,0,.06)]
      ">

        <!-- cursor glow (arancio leggero su bianco) -->
        <div
          class="absolute inset-0 pointer-events-none z-10 rounded-2xl overflow-hidden"
          style="background: radial-gradient(circle at {glowX}% {glowY}%, rgba(251,146,60,.07) 0%, transparent 65%);"
        ></div>

        <!-- ── BANNER ──────────────────────────────────────── -->
        <div class="relative h-28 overflow-hidden rounded-t-2xl banner-bg">
          <div class="absolute inset-0 banner-grid"></div>
          <!-- blobs -->
          <div class="absolute -top-8 -left-6  w-44 h-32 rounded-full bg-orange-400 blur-3xl opacity-40"></div>
          <div class="absolute -top-6 -right-6 w-40 h-28 rounded-full bg-amber-300  blur-3xl opacity-30"></div>
          <!-- accent line top -->
          <div class="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-orange-300 to-transparent"></div>

          <!-- role badge top-right -->
          <Motion
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0  }}
            transition={{ delay: 0.3, duration: 0.4 }}
            let:motion
          >
            <div use:motion class="absolute top-3 right-4">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/20 backdrop-blur-sm border border-white/30 text-white text-[0.62rem] font-bold tracking-widest uppercase font-mono">
                <span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span>
                {roleLabel}
              </span>
            </div>
          </Motion>
        </div>

        <!-- ── AVATAR ROW — fuori dal banner, z alto ─────────
             Il -mt-9 tira su l'avatar sopra il bordo del banner.
             overflow-visible sulla card permette all'avatar di uscire.
        ──────────────────────────────────────────────────────── -->
        <div class="relative flex items-end justify-between px-5 -mt-9 z-30">

          <!-- avatar + spinning ring -->
          <div class="relative w-[72px] h-[72px]">
            <div class="avatar-ring absolute -inset-[3px] rounded-full"></div>
            <div class="
              w-[72px] h-[72px] rounded-full
              bg-white border-[3px] border-white
              flex items-center justify-center select-none
              shadow-md
            ">
              <span class="text-xl font-black text-orange-500 tracking-tighter leading-none">
                {initials}
              </span>
            </div>
          </div>

          <!-- ID pill allineato a destra -->
          <Motion
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1   }}
            transition={{ delay: 0.45, duration: 0.35, type: 'spring', bounce: 0.35 }}
            let:motion
          >
            <span
              use:motion
              class="mb-1 px-2.5 py-1 rounded-lg bg-orange-50 border border-orange-200 text-orange-500 text-[0.65rem] font-black font-mono tracking-wider"
            >
              #{String(user.id ?? '—').padStart(4, '0')}
            </span>
          </Motion>
        </div>

        <!-- ── BODY ────────────────────────────────────────── -->
        <div class="px-5 pb-5 pt-3 relative z-20">

          <!-- name + verified -->
          <div class="flex items-center gap-1.5 mt-2">
            <h2 class="text-lg font-black tracking-tight text-zinc-900 leading-tight">{fullName}</h2>
            <svg viewBox="0 0 20 20" fill="none" class="w-[18px] h-[18px] shrink-0">
              <circle cx="10" cy="10" r="9" fill="#f97316"/>
              <path d="M6 10l3 3 5-5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>

          <!-- email subtitle -->
          <Motion
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0  }}
            transition={{ delay: 0.28, duration: 0.35 }}
            let:motion
          >
            <p use:motion class="text-[0.72rem] text-zinc-400 font-medium tracking-wide mt-0.5 mb-4 truncate">
              {user.email}
            </p>
          </Motion>

          <!-- divider -->
          <div class="h-px bg-gradient-to-r from-orange-200 via-orange-100 to-transparent mb-4"></div>

          <!-- ── INFO ROWS ───────────────────────────────────── -->
          <div class="flex flex-col gap-2.5">

            <!-- saldo -->
            <Motion
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0  }}
              transition={{ delay: 0.32, duration: 0.38 }}
              let:motion
            >
              <div use:motion class="
                flex items-center justify-between px-3.5 py-3 rounded-xl
                bg-orange-50 border border-orange-100
                hover:bg-orange-100 hover:border-orange-200
                transition-all duration-200
              ">
                <div class="flex items-center gap-2.5">
                  <div class="w-7 h-7 rounded-lg bg-orange-100 flex items-center justify-center shrink-0">
                    <svg viewBox="0 0 20 20" fill="none" class="w-3.5 h-3.5 text-orange-500" aria-hidden="true">
                      <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.8" />
                      <path d="M10 6.5V10L12.8 11.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </div>
                  <span class="text-xs text-zinc-500 font-semibold tracking-wide">Saldo ore</span>
                </div>
                <span class="text-sm font-black text-orange-600 font-mono tabular-nums">
                  {fmtSaldo(user.saldo?.valore_saldo_validato)}
                </span>
              </div>
            </Motion>

            <!-- email row -->
            <Motion
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0  }}
              transition={{ delay: 0.40, duration: 0.38 }}
              let:motion
            >
              <div
                use:motion
                class="
                flex items-center justify-between px-3.5 py-3 rounded-xl
                bg-zinc-50 border border-zinc-100
                hover:bg-zinc-100 hover:border-zinc-200
                transition-all duration-200
              "
                role="button"
                tabindex="0"
                on:click={openMail}
                on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && openMail()}
              >
                <div class="flex items-center gap-2.5">
                  <div class="w-7 h-7 rounded-lg bg-zinc-100 flex items-center justify-center shrink-0">
                    <svg viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5 text-zinc-400">
                      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"/>
                      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"/>
                    </svg>
                  </div>
                  <span class="text-xs text-zinc-500 font-semibold tracking-wide">Email</span>
                </div>
                <span class="text-xs font-semibold text-zinc-700 truncate max-w-[150px]">
                  {user.email}
                </span>
              </div>
            </Motion>

          </div>

          <!-- ── FOOTER ──────────────────────────────────────── -->
          <Motion
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            let:motion
          >
            <div use:motion class="mt-4 pt-3.5 border-t border-orange-50 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-orange-400 shadow-[0_0_6px_rgba(251,146,60,.6)] animate-pulse"></span>
                <span class="text-[0.7rem] text-zinc-400 font-medium tracking-wide">Attivo</span>
              </div>
              <span class="text-[0.68rem] text-zinc-400 font-medium">{fullName}</span>
            </div>
          </Motion>

        </div>
        <!-- ╚══ /CARD ══════════════════════════════════════════╝ -->
      </div>
    </div>
  </Motion>
</div>

<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

  :global(body) { font-family: 'Sora', sans-serif; }

  .banner-bg {
    background: linear-gradient(135deg, #f0b799 0%, #f97316 50%, #fb923c 100%);
  }

  .banner-grid {
    background-image:
      linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
    background-size: 24px 24px;
  }

  /* Ring arancio/ambra che ruota dietro le iniziali */
  .avatar-ring {
    background: conic-gradient(#f97316, #fbbf24, #fb923c, #f97316);
    animation: spin 5s linear infinite;
    -webkit-mask: radial-gradient(circle, transparent 50%, black 52%);
            mask: radial-gradient(circle, transparent 50%, black 52%);
  }

  @keyframes spin { to { transform: rotate(360deg); } }
</style>
