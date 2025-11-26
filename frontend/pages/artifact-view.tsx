import React from 'react';
import ReactMarkdown from 'react-markdown';
import { GetServerSideProps } from 'next';

type Props = {
  title: string;
  content: string;
};

export default function ArtifactViewPage({ title, content }: Props) {
  return (
    <main className="page">
      <header className="section__header">
        <h2>{title}</h2>
      </header>
      <section className="section">
        <article className="panel">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      </section>
    </main>
  );
}

export const getServerSideProps: GetServerSideProps = async (context) => {
  const jobId = context.query.jobId as string | undefined;
  const filename = context.query.filename as string | undefined;
  if (!jobId || !filename) return { notFound: true };

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
  try {
    const res = await fetch(`${apiBase}/jobs`);
    if (!res.ok) return { notFound: true };
    const data = await res.json();
    const job = data.items.find((j: any) => j.id === jobId);
    if (!job) return { notFound: true };
    const art = job.artifacts.find((a: any) => a.path && a.path.endsWith('/' + filename));
    if (!art) return { notFound: true };
    return { props: { title: art.title || filename, content: art.content || '' } };
  } catch (err) {
    return { notFound: true };
  }
};
