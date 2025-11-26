import Head from "next/head";
import { useEffect, useState } from "react";

import JobList from "../components/JobList";
import UploadPanel from "../components/UploadPanel";
import { fetchJobs } from "../lib/api";
import type { Job } from "../types/job";

export default function Home() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [notice, setNotice] = useState<string | null>(null);

  const loadJobs = async () => {
    try {
      const { items } = await fetchJobs();
      setJobs(items);
    } catch (err) {
      setNotice("Could not reach the API. Start the backend first.");
    }
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <Head>
        <title>AutoDocs | AI Documentation Generator</title>
      </Head>
      <main className="page">
        <header className="hero">
          <div>
            <p className="eyebrow">AutoDocs</p>
            <h1>AI-generated docs for your micro-SaaS in minutes.</h1>
            <p className="lede">
              Upload a repo, let the queue crunch through it, and get a README, API docs, UML diagrams, test cases, and an
              architecture overview — all powered by LangChain and OpenAI.
            </p>
          </div>
          <div className="hero__cta">
            <span className="pill">FastAPI + Celery</span>
            <span className="pill">Next.js control room</span>
            <span className="pill">Postgres history</span>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}

        <UploadPanel
          onUploaded={(job) => {
            setNotice("Job queued. Worker will generate artifacts shortly.");
            setJobs((prev) => [job, ...prev]);
          }}
          onError={(message) => setNotice(message)}
        />

        <section className="section">
          <div className="section__header">
            <div>
              <p className="eyebrow">Job timeline</p>
              <h2>Recent generations</h2>
            </div>
            <button className="ghost" onClick={loadJobs}>
              Refresh
            </button>
          </div>
          <JobList jobs={jobs} />
        </section>
      </main>
    </>
  );
}
