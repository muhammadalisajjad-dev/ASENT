import React from 'react';
import {Series} from 'remotion';
import {CAVRFilm, CAVR_FRAMES, CAVREvidence} from './cavr-film';
import {SATRAFilm, SATRA_FRAMES, SATRAEvidence} from './satra-film';
import {SableFilm, SABLE_FRAMES, Evidence as SABLEEvidence} from './sable-film';
import {IntegratedFilm, INTEGRATED_FRAMES, IntegratedEvidence} from './integrated-film';

export const FULL_FRAMES = CAVR_FRAMES + SATRA_FRAMES + SABLE_FRAMES + INTEGRATED_FRAMES; // 600 + 600 + 600 + 450 = 2250 frames (75s)

export type FullEvidence = {
  cavr: CAVREvidence;
  satra: SATRAEvidence;
  sable: SABLEEvidence;
  integrated: IntegratedEvidence;
};

export type Props = {
  evidence: FullEvidence;
};

export const FullFilm: React.FC<Props> = ({evidence}) => {
  return (
    <Series>
      <Series.Sequence durationInFrames={CAVR_FRAMES}>
        <CAVRFilm evidence={evidence.cavr} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SATRA_FRAMES}>
        <SATRAFilm evidence={evidence.satra} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={SABLE_FRAMES}>
        <SableFilm evidence={evidence.sable} />
      </Series.Sequence>
      <Series.Sequence durationInFrames={INTEGRATED_FRAMES}>
        <IntegratedFilm evidence={evidence.integrated} />
      </Series.Sequence>
    </Series>
  );
};
