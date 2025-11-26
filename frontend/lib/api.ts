import axios from "axios";

import type { Job, JobListResponse } from "../types/job";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
});

export async function uploadJob(file: File): Promise<Job> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post<Job>("/jobs/upload", form, {
    headers: { "Content-Type": "multipart/form-data" }
  });
  return data;
}

export async function fetchJobs(): Promise<JobListResponse> {
  const { data } = await api.get<JobListResponse>("/jobs");
  return data;
}
