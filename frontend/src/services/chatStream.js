import { getFreshAuthToken, API_HOST } from './api';
import { auth } from '../firebase';

export async function streamMessage({
  conversationId,
  content,
  model,
  webSearch = false,
  fileIds = null,
  attachments = null,
  signal,
  onToken,
  onDone,
  onError,
}) {
  let token = await getFreshAuthToken();
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const payloadBody = JSON.stringify({
    content,
    model,
    web_search: webSearch,
    file_ids: fileIds,
    attachments,
  });

  try {
    let response = await fetch(`${API_HOST}/api/v1/conversations/${conversationId}/messages/stream`, {
      method: 'POST',
      headers,
      body: payloadBody,
      signal,
    });

    // If 401 Unauthorized occurs and Firebase user exists, force token refresh and retry once
    if (response.status === 401 && auth?.currentUser) {
      try {
        const freshToken = await getFreshAuthToken(true);
        if (freshToken) {
          headers['Authorization'] = `Bearer ${freshToken}`;
          response = await fetch(`${API_HOST}/api/v1/conversations/${conversationId}/messages/stream`, {
            method: 'POST',
            headers,
            body: payloadBody,
            signal,
          });
        }
      } catch (retryErr) {
        console.warn('Stream auth retry error:', retryErr);
      }
    }

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      throw new Error(errJson.detail || `Server returned error (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep last incomplete line

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith('data: ')) continue;

        const payloadStr = trimmed.slice(6).trim();
        try {
          const payload = JSON.parse(payloadStr);

          if (payload.token && onToken) {
            onToken(payload.token);
          }

          if (payload.error) {
            if (onError) onError(payload.error);
          }

          if (payload.done && onDone) {
            onDone(payload);
          }
        } catch (e) {
          console.error('Failed to parse SSE JSON:', payloadStr, e);
        }
      }
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      console.log('Stream aborted by user');
      if (onDone) onDone({ aborted: true });
    } else {
      if (onError) onError(err.message || 'Stream connection failed');
    }
  }
}
