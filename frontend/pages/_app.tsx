import type { AppProps } from "next/app";

import "../styles/globals.css";

export default function AutoDocsApp({ Component, pageProps }: AppProps) {
  return <Component {...pageProps} />;
}
