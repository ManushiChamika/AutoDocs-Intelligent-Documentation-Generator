import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ArtifactView() {
  const router = useRouter();
  const { jobId, filename } = router.query as { jobId: string; filename: string };
  const [content, setContent] = useState<string | null>(null);
  const [title, setTitle] = useState<string>(filename || 'Artifact');

  useEffect(() => {
    if (!jobId || !filename) return;
    const fetchJob = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'}/jobs`);
        const data = await res.json();
        const job = data.items.find((j: any) => j.id === jobId);
        if (!job) {
          setContent('# Not found\nJob not found');
          return;
        }
        const art = job.artifacts.find((a: any) => a.path && a.path.endsWith('/' + filename));
        if (!art) {
          setContent('# Not found\nArtifact not found');
          return;
        }
        setTitle(art.title || filename);
        setContent(art.content || '# Empty');
      } catch (err) {
        setContent('# Error\nCould not fetch artifact');
      }
    };
    fetchJob();
  }, [jobId, filename]);

  return (
    <main className="page">
      <header className="section__header">
        <h2>{title}</h2>
      </header>
      <section className="section">
        {content ? (
          <article className="panel">
            <ReactMarkdown>{content}</ReactMarkdown>
          </article>
        ) : (
          <p>Loading...</p>
        )}
      </section>
    </main>
  );
}
