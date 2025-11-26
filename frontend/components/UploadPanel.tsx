import { useState } from "react";

import { uploadJob } from "../lib/api";
import type { Job } from "../types/job";

type Props = {
  onUploaded: (job: Job) => void;
  onError: (message: string) => void;
};

export default function UploadPanel({ onUploaded, onError }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async () => {
    if (!file) {
      onError("Pick a file first. Zip works best for full repos.");
      return;
    }
    setIsUploading(true);
    try {
      const job = await uploadJob(file);
      onUploaded(job);
      setFile(null);
    } catch (err) {
      onError("Upload failed. Is the backend running?");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="panel">
      <div className="panel__header">
        <div className="eyebrow">AI-Driven Pipeline</div>
        <h2>Upload a codebase and let AutoDocs craft the docs.</h2>
        <p>We queue the job, parse the repo, and ask the LLM for README, API docs, UML, tests, and an architecture overview.</p>
      </div>

      <div className="upload-box">
        <label htmlFor="upload-input" className="upload-box__label">
          <span className="upload-box__title">{file?.name || "Drop a project zip or choose a folder snapshot"}</span>
          <span className="upload-box__hint">Max 50MB. Zips preserve structure.</span>
          <input
            id="upload-input"
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="upload-box__input"
          />
        </label>
        <button className="primary" onClick={handleUpload} disabled={isUploading}>
          {isUploading ? "Uploading…" : "Generate Docs"}
        </button>
      </div>

      <div className="pill-row">
        <span className="pill">Queue-backed</span>
        <span className="pill">LangChain + OpenAI</span>
        <span className="pill">Postgres audit trail</span>
        <span className="pill">UML + Tests</span>
      </div>
    </div>
  );
}
