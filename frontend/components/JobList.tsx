import clsx from "clsx";

import type { Job } from "../types/job";

type Props = {
  jobs: Job[];
};

const statusCopy: Record<Job["status"], string> = {
  pending: "Queued",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed"
};

export default function JobList({ jobs }: Props) {
  if (!jobs.length) {
    return (
      <div className="panel muted">
        <p>No jobs yet. Upload a project and watch the pipeline light up.</p>
      </div>
    );
  }

  return (
    <div className="grid">
      {jobs.map((job) => (
        <article key={job.id} className="card">
          <div className="card__header">
            <div>
              <p className="eyebrow">Job</p>
              <h3>{job.filename}</h3>
              <p className="timestamp">Created {new Date(job.created_at).toLocaleString()}</p>
            </div>
            <div className={clsx("badge", job.status)}>
              {statusCopy[job.status]} · {job.progress}%
            </div>
          </div>

          {job.error_message && <p className="error">{job.error_message}</p>}

          <div className="artifacts">
            {job.artifacts.length ? (
              job.artifacts.map((artifact) => {
                const filename = artifact.path ? artifact.path.split("/").pop() : `${artifact.type}.md`;
                const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/jobs/${job.id}/artifacts/${filename}`;
                return (
                  <a
                    key={artifact.id}
                    className="artifact"
                    href={downloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <p className="artifact__title">{artifact.title}</p>
                    <p className="artifact__type">{artifact.type}</p>
                  </a>
                );
              })
            ) : (
              <p className="muted">Artifacts will appear as soon as the worker finishes.</p>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}
