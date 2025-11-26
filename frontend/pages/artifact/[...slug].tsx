import React from 'react';
import ReactMarkdown from 'react-markdown';
import { GetServerSideProps } from 'next';

type Props = {
  title: string;
  content: string;
};

export default function ArtifactCatchAll({ title, content }: Props) {
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
  const slug = context.params?.slug as string[] | undefined;
  if (!slug || slug.length < 2) return { notFound: true };

  const jobId = slug[0];
  // filename may contain dots, join remaining parts
  const filename = slug.slice(1).join('/');

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

  try {
    const res = await fetch(`${apiBase}/jobs`);
    if (!res.ok) return { notFound: true };
    const data = await res.json();
    const job = data.items.find((j: any) => j.id === jobId);
    if (!job) return { notFound: true };

    const art = job.artifacts.find((a: any) => a.path && a.path.endsWith('/' + filename));
    if (!art) return { notFound: true };

    return {
      props: {
        title: art.title || filename,
        content: art.content || '',
      },
    };
  } catch (err) {
    return { notFound: true };
  }
};
