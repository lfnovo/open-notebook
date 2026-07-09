interface HeroGraphicProps {
  size?: number;
  className?: string;
  withBackdrop?: boolean;
}

export function HeroGraphic({
  size = 176,
  className = "",
  withBackdrop = true,
}: HeroGraphicProps) {
  return (
    <div
      className={`relative inline-flex items-center justify-center ${className}`}
      style={{ width: size, height: size }}
    >
      {withBackdrop ? (
        <div
          className="absolute inset-0 rounded-3xl bg-black shadow-[0_0_60px_rgba(65,209,255,0.12)]"
          aria-hidden
        />
      ) : null}
      <svg
        width={size * 0.72}
        height={size * 0.72}
        viewBox="0 0 240 240"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="relative z-10"
        aria-hidden
      >
        <defs>
          <linearGradient id="hero-node-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#bd34fe" />
            <stop offset="100%" stopColor="#41d1ff" />
          </linearGradient>
          <linearGradient id="hero-line-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#bd34fe" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#41d1ff" stopOpacity="0.35" />
          </linearGradient>
        </defs>

        <g className="hero-connections">
          <path d="M120 80L80 120" stroke="url(#hero-line-gradient)" strokeWidth="2" />
          <path d="M120 80L160 120" stroke="url(#hero-line-gradient)" strokeWidth="2" />
          <path d="M80 120L120 160" stroke="url(#hero-line-gradient)" strokeWidth="2" />
          <path d="M160 120L120 160" stroke="url(#hero-line-gradient)" strokeWidth="2" />
          <path d="M80 120L160 120" stroke="url(#hero-line-gradient)" strokeWidth="2" />
        </g>

        <g className="hero-nodes">
          <circle cx="120" cy="80" r="20" fill="url(#hero-node-gradient)" />
          <circle
            cx="120"
            cy="80"
            r="24"
            stroke="url(#hero-node-gradient)"
            strokeWidth="1"
            fill="none"
          />
          <circle cx="80" cy="120" r="16" fill="url(#hero-node-gradient)" />
          <circle
            cx="80"
            cy="120"
            r="20"
            stroke="url(#hero-node-gradient)"
            strokeWidth="1"
            fill="none"
          />
          <circle cx="160" cy="120" r="16" fill="url(#hero-node-gradient)" />
          <circle
            cx="160"
            cy="120"
            r="20"
            stroke="url(#hero-node-gradient)"
            strokeWidth="1"
            fill="none"
          />
          <circle cx="120" cy="160" r="18" fill="url(#hero-node-gradient)" />
          <circle
            cx="120"
            cy="160"
            r="22"
            stroke="url(#hero-node-gradient)"
            strokeWidth="1"
            fill="none"
          />
        </g>
      </svg>
    </div>
  );
}
