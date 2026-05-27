/**
 * API client for Employee Self-Service (ESS) endpoints.
 */

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const error = await res
      .json()
      .catch(() => ({ detail: { message: res.statusText } }));
    throw new Error(error.detail?.message || `Request failed: ${res.status}`);
  }
  return res.json();
}

// Documents

export interface ESSDocument {
  id: string;
  file_name: string;
  document_type: string;
  file_size: number;
  uploaded_at: string;
}

export interface ESSDocumentDownload {
  download_url: string;
  file_name: string;
  expires_in_seconds: number;
}

export async function getDocuments(
  documentType?: string,
): Promise<ESSDocument[]> {
  const params = new URLSearchParams();
  if (documentType) {
    params.set("document_type", documentType);
  }
  const query = params.toString();
  const url = `/api/v1/ess/documents${query ? `?${query}` : ""}`;
  const res = await fetch(url);
  return handleResponse<ESSDocument[]>(res);
}

export async function getDocumentDownloadUrl(
  documentId: string,
): Promise<ESSDocumentDownload> {
  const res = await fetch(`/api/v1/ess/documents/${documentId}/download`);
  return handleResponse<ESSDocumentDownload>(res);
}
