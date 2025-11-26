export type Artifact = {
  id: string;
  type: string;
  title: string;
  path?: string | null;
  content?: string | null;
  created_at: string;
};

export type Job = {
  id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  artifacts: Artifact[];
};

export type JobListResponse = {
  items: Job[];
  total: number;
};
