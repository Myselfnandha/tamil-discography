// js/lyrics-canvas.js
// Renders an Apple Music-style animated fluid gradient background based on cover art colors

export class LyricsCanvasBackground {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement ? canvasElement.getContext('2d') : null;
        this.blobs = [];
        this.animId = null;
        this.width = 0;
        this.height = 0;
        this.colors = ['#1e1b4b', '#4338ca', '#312e81', '#0f172a'];
    }

    init() {
        if (!this.canvas || !this.ctx) return;
        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        if (!this.canvas) return;
        const rect = this.canvas.getBoundingClientRect();
        this.width = rect.width || window.innerWidth;
        this.height = rect.height || window.innerHeight;
        this.canvas.width = this.width;
        this.canvas.height = this.height;
        this.createBlobs();
    }

    setColors(colorList) {
        if (Array.isArray(colorList) && colorList.length >= 2) {
            this.colors = colorList;
        }
        this.createBlobs();
    }

    createBlobs() {
        const w = this.width || 800;
        const h = this.height || 600;

        this.blobs = [
            {
                x: w * 0.2,
                y: h * 0.3,
                radius: Math.min(w, h) * 0.45,
                color: this.colors[0] || '#4338ca',
                vx: 0.4,
                vy: 0.3,
                phase: 0,
            },
            {
                x: w * 0.7,
                y: h * 0.25,
                radius: Math.min(w, h) * 0.5,
                color: this.colors[1] || '#312e81',
                vx: -0.3,
                vy: 0.5,
                phase: Math.PI / 2,
            },
            {
                x: w * 0.3,
                y: h * 0.75,
                radius: Math.min(w, h) * 0.4,
                color: this.colors[2] || '#1e1b4b',
                vx: 0.5,
                vy: -0.4,
                phase: Math.PI,
            },
            {
                x: w * 0.8,
                y: h * 0.7,
                radius: Math.min(w, h) * 0.48,
                color: this.colors[3] || '#0f172a',
                vx: -0.4,
                vy: -0.3,
                phase: (3 * Math.PI) / 2,
            },
        ];
    }

    start() {
        if (this.animId) return;
        this.init();
        const render = () => {
            this.draw();
            this.animId = requestAnimationFrame(render);
        };
        this.animId = requestAnimationFrame(render);
    }

    stop() {
        if (this.animId) {
            cancelAnimationFrame(this.animId);
            this.animId = null;
        }
    }

    draw() {
        if (!this.ctx || this.width === 0 || this.height === 0) return;
        const ctx = this.ctx;
        const w = this.width;
        const h = this.height;

        // Dark background base
        ctx.fillStyle = '#0a0a0c';
        ctx.fillRect(0, 0, w, h);

        ctx.globalCompositeOperation = 'screen';

        const time = Date.now() * 0.001;

        for (const blob of this.blobs) {
            // Sinusoidal motion offset
            const offsetX = Math.sin(time * blob.vx + blob.phase) * (w * 0.15);
            const offsetY = Math.cos(time * blob.vy + blob.phase) * (h * 0.15);
            const cx = blob.x + offsetX;
            const cy = blob.y + offsetY;

            const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, blob.radius);
            grad.addColorStop(0, blob.color);
            grad.addColorStop(0.6, blob.color);
            grad.addColorStop(1, 'rgba(0, 0, 0, 0)');

            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(cx, cy, blob.radius, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.globalCompositeOperation = 'source-over';
    }
}
