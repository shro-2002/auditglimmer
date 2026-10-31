"use client";

import { urls } from "@/lib/api";
import type { Decision, DetectionBundle, ImageAsset } from "@/lib/types";

const VIEWPORT_MAX_VH = 70;
const LABEL_SCALE = 45; // label font = image width / LABEL_SCALE
const DEFAULT_TONE = "#2dd4bf";

export const DECISION_HEX: Record<Decision, string> = {
  VERIFIED: "#5eead4",
  PROBABLE: "#fcd34d",
  WEAK: "#fdba74",
  MISMATCHED: "#fca5a5",
  NOT_IN_REGISTER: "#7dd3fc",
  EVIDENCE_UNUSABLE: "#a8a29e",
};

export function regionTone(bundle: DetectionBundle): string {
  return bundle.decision ? DECISION_HEX[bundle.decision.decision] : DEFAULT_TONE;
}

type Props = {
  image: ImageAsset;
  regions: DetectionBundle[];
  selectedId: string | null;
  hoveredId: string | null;
  showMasks: boolean;
  onSelect: (detectionId: string) => void;
  onHover: (detectionId: string | null) => void;
};

/**
 * Container takes the image's natural aspect ratio, so <img> and <svg viewBox="0 0 w h"> share one box
 * and masks align with no further math (contract invariant 1).
 */
export function MaskViewer({ image, regions, selectedId, hoveredId, showMasks, onSelect, onHover }: Props) {
  const ratio = image.width / image.height;
  const labelSize = Math.max(image.width / LABEL_SCALE, 10);

  return (
    <div
      className="relative mx-auto overflow-hidden rounded-md border border-line bg-canvas"
      style={{ aspectRatio: `${image.width} / ${image.height}`, width: `min(100%, calc(${VIEWPORT_MAX_VH}vh * ${ratio}))` }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element -- dynamic API-hosted image, exact pixel box needed */}
      <img
        src={urls.image(image)}
        alt={`Inspected photo ${image.filename}`}
        width={image.width}
        height={image.height}
        className="absolute inset-0 h-full w-full select-none"
        draggable={false}
      />
      <svg
        data-testid="mask-overlay"
        viewBox={`0 0 ${image.width} ${image.height}`}
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-0 h-full w-full"
        aria-hidden="true"
        onMouseLeave={() => onHover(null)}
      >
        {regions.map((bundle, index) => {
          const { detection } = bundle;
          const [x1, y1, x2, y2] = detection.mask.bounds;
          const sx = (x2 - x1) / detection.mask.raster_w;
          const sy = (y2 - y1) / detection.mask.raster_h;
          const tone = regionTone(bundle);
          const isSelected = detection.id === selectedId;
          const isHot = isSelected || detection.id === hoveredId;
          return (
            <g
              key={detection.id}
              className="cursor-pointer"
              onClick={() => onSelect(detection.id)}
              onMouseEnter={() => onHover(detection.id)}
            >
              <rect
                x={x1}
                y={y1}
                width={x2 - x1}
                height={y2 - y1}
                fill="transparent"
                stroke={tone}
                strokeWidth={isSelected ? 2.5 : 1.25}
                strokeDasharray={isSelected ? undefined : "6 4"}
                vectorEffect="non-scaling-stroke"
                opacity={isHot ? 1 : 0.7}
              />
              {showMasks && (
                <g transform={`translate(${x1} ${y1}) scale(${sx} ${sy})`}>
                  <path
                    data-testid={`mask-path-${detection.id}`}
                    d={detection.mask.svg_path}
                    fill={tone}
                    fillOpacity={isHot ? 0.45 : 0.22}
                    fillRule="evenodd"
                    stroke={tone}
                    strokeWidth={isSelected ? 2 : 1}
                    vectorEffect="non-scaling-stroke"
                  />
                </g>
              )}
              <g transform={`translate(${x1} ${Math.max(y1 - labelSize * 1.4, 0)})`}>
                <rect width={labelSize * 2.2} height={labelSize * 1.4} rx={labelSize * 0.25} fill={tone} />
                <text
                  x={labelSize * 1.1}
                  y={labelSize * 1.02}
                  textAnchor="middle"
                  fontSize={labelSize}
                  fontWeight={700}
                  fill="#04201c"
                  fontFamily="ui-monospace, monospace"
                >
                  {index + 1}
                </text>
              </g>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
