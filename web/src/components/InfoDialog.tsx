import { useRef } from "react";

import { InfoIcon } from "./BrandMark";

export function InfoDialog() {
  const dialogRef = useRef<HTMLDialogElement>(null);

  return (
    <>
      <button
        aria-label="项目说明"
        className="info-trigger"
        onClick={() => dialogRef.current?.showModal()}
        type="button"
      >
        <span className="info-trigger__desktop">项目说明</span>
        <span className="info-trigger__mobile"><InfoIcon /></span>
      </button>
      <dialog className="info-dialog" ref={dialogRef} onClick={(event) => {
        if (event.target === event.currentTarget) {
          event.currentTarget.close();
        }
      }}>
        <div className="info-dialog__content">
          <button aria-label="关闭项目说明" className="dialog-close" onClick={() => dialogRef.current?.close()} type="button">×</button>
          <p className="dialog-kicker">Gomoku-AI</p>
          <h2>在浏览器里，和真正的搜索引擎下一局。</h2>
          <p>支持人机、本地双人和 AI 对 AI。这是自由规则五子棋：黑棋先手，任意方向形成五连或更长连线即可获胜。</p>
          <dl>
            <div><dt>棋盘</dt><dd>15 × 15</dd></div>
            <div><dt>算法</dt><dd>Alpha-Beta v5</dd></div>
            <div><dt>运行方式</dt><dd>Rust WebAssembly，本地计算</dd></div>
          </dl>
          <p className="info-dialog__privacy">棋局不会上传服务器；刷新页面即可清空当前对局。</p>
          <a href="https://github.com/firefighter-eric/Gomoku-AI" rel="noreferrer" target="_blank">查看 GitHub 项目</a>
        </div>
      </dialog>
    </>
  );
}
