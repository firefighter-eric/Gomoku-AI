export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 48 48" aria-hidden="true">
      <circle cx="24" cy="24" r="22.5" fill="none" stroke="currentColor" strokeWidth="1" />
      <circle cx="24" cy="10.5" r="4.5" fill="#171716" />
      <circle cx="14.5" cy="19" r="4.5" fill="#171716" />
      <circle cx="33.5" cy="19" r="4.5" fill="#171716" />
      <circle cx="19" cy="29.5" r="4.5" fill="#171716" />
      <circle cx="29.5" cy="34" r="4.5" fill="#f8f6ef" stroke="#8d8980" strokeWidth="0.8" />
    </svg>
  );
}

export function InfoIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="9.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 10.4v6" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.7" />
      <circle cx="12" cy="7.2" r="1.05" fill="currentColor" />
    </svg>
  );
}

export function SoundIcon({ enabled }: { enabled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4.5 9.25h3.2L12 5.8v12.4l-4.3-3.45H4.5z" fill="none" stroke="currentColor" strokeLinejoin="round" strokeWidth="1.5" />
      {enabled ? (
        <>
          <path d="M15 9.1a4 4 0 0 1 0 5.8" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
          <path d="M17.5 6.8a7.2 7.2 0 0 1 0 10.4" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
        </>
      ) : (
        <path d="m15.2 9.2 4.6 5.6m0-5.6-4.6 5.6" fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="1.5" />
      )}
    </svg>
  );
}

export function ChevronIcon() {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="m5.5 7.5 4.5 4.5 4.5-4.5" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" />
    </svg>
  );
}
