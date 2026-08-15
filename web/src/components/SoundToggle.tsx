import { SoundIcon } from "./BrandMark";

interface SoundToggleProps {
  enabled: boolean;
  onToggle: () => void;
}

export function SoundToggle({ enabled, onToggle }: SoundToggleProps) {
  const label = enabled ? "关闭音效" : "开启音效";
  return (
    <button
      aria-label={label}
      aria-pressed={enabled}
      className="sound-toggle"
      onClick={onToggle}
      title={label}
      type="button"
    >
      <SoundIcon enabled={enabled} />
      <span className="sound-toggle__label">音效</span>
    </button>
  );
}
