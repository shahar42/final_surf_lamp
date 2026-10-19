/**
 * Jellyfish Background
 *
 * Ambient canvas animation of a few jellyfish drifting up behind the lamp.
 * - Visibility is owned by CSS (dashboard.css): mobile only, Lamp tab only
 * - This module only runs the render loop while the canvas is displayed
 */
const Jellyfish = (function() {
    // Total height of one jellyfish (bell + tentacles) in CSS px.
    // 46px matches the surf condition icons (e.g. the Period clock).
    const SIZE = 46;
    const SIZE_VARIATION = 0.15;     // +/- 15% per jellyfish
    const COUNT = 3;
    const RISE_SPEED = 10;           // average upward drift, px/s
    const TENTACLES = 7;
    const ORAL_ARMS = 3;
    const SEGMENTS = 12;

    let canvas, ctx;
    let width = 0, height = 0;
    let jellies = [];
    let rafId = null;
    let lastTime = 0;
    let elapsed = 0;

    function init() {
        canvas = document.getElementById('jellyfishCanvas');
        if (!canvas) return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

        ctx = canvas.getContext('2d');
        resize();
        jellies = Array.from({ length: COUNT }, (_, i) => createJelly(i, true));

        window.addEventListener('resize', resize);

        // Re-check whenever something can change the canvas's visibility
        const lampSection = document.querySelector('.dashboard-section[data-tab="lamp"]');
        if (lampSection) {
            new MutationObserver(syncRunning).observe(lampSection, {
                attributes: true,
                attributeFilter: ['class']
            });
        }
        window.matchMedia('(max-width: 1023px)').addEventListener('change', syncRunning);
        document.addEventListener('visibilitychange', syncRunning);

        syncRunning();
    }

    function isVisible() {
        return !document.hidden && getComputedStyle(canvas).display !== 'none';
    }

    function syncRunning() {
        if (isVisible()) {
            if (rafId === null) {
                lastTime = performance.now();
                rafId = requestAnimationFrame(frame);
            }
        } else if (rafId !== null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    }

    function resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        width = window.innerWidth;
        height = window.innerHeight;
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    function createJelly(index, initial) {
        const size = SIZE * (1 + (Math.random() * 2 - 1) * SIZE_VARIATION);
        // Spread across the width in lanes so they don't bunch up
        const lane = (index + 0.5 + (Math.random() - 0.5) * 0.6) / COUNT;
        return {
            x: width * lane,
            y: initial ? Math.random() * height : height + size,
            size,
            bellWidth: size * 0.65,
            bellHeight: size * 0.4,
            speed: RISE_SPEED * (0.7 + Math.random() * 0.6),
            phase: Math.random() * Math.PI * 2,
            pulseRate: 0.5 + Math.random() * 0.3,     // pulses per second
            swayPhase: Math.random() * Math.PI * 2,
            tilt: 0,
            hue: 185 + Math.random() * 45,            // cyan -> blue-violet
            alpha: 0.6 + Math.random() * 0.3,
            offsets: Array.from({ length: TENTACLES + ORAL_ARMS }, () => Math.random() * Math.PI * 2)
        };
    }

    function frame(now) {
        // Clamp dt so a resumed tab doesn't teleport the jellyfish
        const dt = Math.min((now - lastTime) / 1000, 0.05);
        lastTime = now;
        elapsed += dt;

        ctx.clearRect(0, 0, width, height);
        ctx.globalCompositeOperation = 'lighter';

        jellies.forEach((j, i) => {
            update(j, dt);
            if (j.y + j.size < -10) jellies[i] = createJelly(i, false);
            draw(jellies[i]);
        });

        rafId = requestAnimationFrame(frame);
    }

    function update(j, dt) {
        j.phase += Math.PI * 2 * j.pulseRate * dt;
        const contraction = Math.max(0, Math.sin(j.phase));
        // Thrust comes from the bell contracting, then it coasts
        j.y -= j.speed * (0.4 + 1.2 * contraction) * dt;

        const sway = Math.sin(elapsed * 0.3 + j.swayPhase);
        j.x += sway * 4 * dt;
        j.tilt = sway * 0.15;
    }

    function hsla(h, s, l, a) {
        return `hsla(${h}, ${s}%, ${l}%, ${a})`;
    }

    function draw(j) {
        const contraction = Math.max(0, Math.sin(j.phase));
        const bw = j.bellWidth * (1 - 0.18 * contraction);
        const bh = j.bellHeight * (1 + 0.12 * contraction);
        const tentacleLength = (j.size - j.bellHeight) * (1 - 0.08 * contraction);
        const scale = j.size / SIZE;
        const a = j.alpha;

        ctx.save();
        ctx.translate(j.x, j.y);
        ctx.rotate(j.tilt);

        // Soft bioluminescent halo
        const halo = ctx.createRadialGradient(0, bh * 0.5, 0, 0, bh * 0.5, j.size * 0.8);
        halo.addColorStop(0, hsla(j.hue, 90, 65, 0.10 * a));
        halo.addColorStop(1, hsla(j.hue, 90, 65, 0));
        ctx.fillStyle = halo;
        ctx.fillRect(-j.size, -j.size * 0.5, j.size * 2, j.size * 2);

        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';

        // Tentacles: thin, long, fading toward the tips
        const fade = ctx.createLinearGradient(0, bh, 0, bh + tentacleLength);
        fade.addColorStop(0, hsla(j.hue, 80, 80, 0.45 * a));
        fade.addColorStop(1, hsla(j.hue, 80, 80, 0));
        ctx.strokeStyle = fade;
        ctx.lineWidth = 0.6;
        for (let k = 0; k < TENTACLES; k++) {
            const rimX = (k / (TENTACLES - 1) - 0.5) * bw * 0.85;
            drawStrand(rimX, bh, tentacleLength, j.offsets[k], 3.5 * scale, 4, 0.3);
        }

        // Oral arms: shorter, thicker, ruffled strands from the center
        const armFade = ctx.createLinearGradient(0, bh, 0, bh + tentacleLength * 0.6);
        armFade.addColorStop(0, hsla(j.hue + 20, 70, 75, 0.35 * a));
        armFade.addColorStop(1, hsla(j.hue + 20, 70, 75, 0));
        ctx.strokeStyle = armFade;
        ctx.lineWidth = 1.6 * scale;
        for (let k = 0; k < ORAL_ARMS; k++) {
            const rimX = (k / (ORAL_ARMS - 1) - 0.5) * bw * 0.25;
            drawStrand(rimX, bh * 0.9, tentacleLength * 0.6, j.offsets[TENTACLES + k], 2 * scale, 9, 0);
        }

        // Bell: dome with a scalloped margin
        ctx.beginPath();
        ctx.moveTo(-bw / 2, bh);
        ctx.bezierCurveTo(-bw / 2, -bh * 0.3, bw / 2, -bh * 0.3, bw / 2, bh);
        const scallops = 6;
        for (let s = 1; s <= scallops; s++) {
            const x0 = bw / 2 - (bw * (s - 0.5)) / scallops;
            const x1 = bw / 2 - (bw * s) / scallops;
            ctx.quadraticCurveTo(x0, bh * 1.12, x1, bh);
        }
        ctx.closePath();

        const bellFill = ctx.createRadialGradient(0, bh * 0.3, 0, 0, bh * 0.3, bw * 0.6);
        bellFill.addColorStop(0, hsla(j.hue, 80, 80, 0.40 * a));
        bellFill.addColorStop(1, hsla(j.hue, 80, 60, 0.12 * a));
        ctx.fillStyle = bellFill;
        ctx.fill();
        ctx.strokeStyle = hsla(j.hue, 90, 85, 0.45 * a);
        ctx.lineWidth = 0.8;
        ctx.stroke();

        // Inner gonads: four faint loops seen through the bell
        ctx.strokeStyle = hsla(j.hue + 30, 90, 85, 0.30 * a);
        ctx.lineWidth = 0.7;
        for (let g = 0; g < 4; g++) {
            const angle = (g / 4) * Math.PI * 2 + Math.PI / 4;
            ctx.beginPath();
            ctx.ellipse(
                Math.cos(angle) * bw * 0.14, bh * 0.5 + Math.sin(angle) * bh * 0.14,
                bw * 0.08, bh * 0.12, angle, 0, Math.PI * 2
            );
            ctx.stroke();
        }

        // Specular highlight on the dome
        ctx.fillStyle = hsla(0, 0, 100, 0.18 * a);
        ctx.beginPath();
        ctx.ellipse(-bw * 0.18, bh * 0.22, bw * 0.12, bh * 0.08, -0.5, 0, Math.PI * 2);
        ctx.fill();

        ctx.restore();
    }

    /**
     * Draw one wavy strand hanging from (x, y)
     * @param {number} amplitude - sideways wave size at the tip
     * @param {number} frequency - waves along the strand
     * @param {number} taper - how much the strand drifts toward the center
     */
    function drawStrand(x, y, length, offset, amplitude, frequency, taper) {
        ctx.beginPath();
        ctx.moveTo(x, y);
        for (let s = 1; s <= SEGMENTS; s++) {
            const f = s / SEGMENTS;
            const wave = Math.sin(elapsed * 2.2 - f * frequency + offset) * f * amplitude;
            ctx.lineTo(x * (1 - f * taper) + wave, y + f * length);
        }
        ctx.stroke();
    }

    return { init };
})();

document.addEventListener('DOMContentLoaded', Jellyfish.init);
