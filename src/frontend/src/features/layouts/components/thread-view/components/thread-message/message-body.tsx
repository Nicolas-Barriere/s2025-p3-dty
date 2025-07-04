import { useCallback, useEffect, useMemo, useRef } from "react";
import DomPurify from "dompurify";

type MessageBodyProps = {
    rawHtmlBody: string;
    rawTextBody: string;
}

const CSP = [
    // Allow images from our domain, data URIs, blob URLs, and https sources
    "img-src 'self' data: blob: http://localhost:3000 http://localhost:8071 https:",
    // Disable everything else by default
    "default-src 'none'",
    // No scripts at all
    "script-src 'none'",
    // No styles from external sources
    "style-src 'unsafe-inline'",
    // No fonts
    "font-src 'none'",
    // No connections
    "connect-src 'none'",
    // No media
    "media-src 'none'",
    // No objects/embeds
    "object-src 'none'",
    // No prefetch
    "prefetch-src 'none'",
    // No frames
    "child-src 'none'",
    "frame-src 'none'",
    // No workers
    "worker-src 'none'",
    // No frame ancestors
    "frame-ancestors 'none'",
  ].join('; ');

const MessageBody = ({ rawHtmlBody, rawTextBody }: MessageBodyProps) => {
    const iframeRef = useRef<HTMLIFrameElement>(null);

    DomPurify.addHook(
        'afterSanitizeAttributes',
        function (node) {
            // Allow anchor tags to be opened in the parent window if the href is an anchor
            // Other links are opened in a new tab and safe rel attributes is set
            if(node.tagName === 'A') {
                if (!node.getAttribute('href')?.startsWith('#')) {
                    node.setAttribute('target', '_blank');
                }
                node.setAttribute('rel', 'noopener noreferrer');
            }
            
            // Handle problematic image sources
            if(node.tagName === 'IMG') {
                const src = node.getAttribute('src');
                if (src?.startsWith('cid:')) {
                    // Replace cid: images with a placeholder or remove them
                    node.setAttribute('src', 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTkgMTJsMS4yNS0xLjI1IDIuNSAyLjUgMy41LTMuNSAxLjI1IDEuMjUtNC43NSA0Ljc1TDkgMTJ6IiBmaWxsPSIjOTk5Ii8+Cjwvc3ZnPgo=');
                    node.setAttribute('alt', '[Embedded image not available]');
                    node.setAttribute('title', 'Embedded image removed for security');
                }
            }
        }
    );

    const sanitizedHtmlBody = useMemo(() => {
        return DomPurify.sanitize(rawHtmlBody || rawTextBody, {
            FORBID_TAGS: ['script', 'object', 'iframe', 'embed', 'audio', 'video'],
            ADD_ATTR: ['target', 'rel'],
        });
    }, []);

    const wrappedHtml = useMemo(() => {
        return `
            <html>
            <head>
                <meta http-equiv="Content-Security-Policy" content="${CSP}">
                <base target="_blank">
                <style>
                html, body {
                    margin: 0;
                    padding: 0;
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    font-size: 14px;
                    color: #24292e;
                }
                img { max-width: 100%; height: auto; }
                a { color: #0366d6; text-decoration: none; }
                a:hover { text-decoration: underline; }
                blockquote {
                    margin: 0 0 1em;
                    padding: 0 1em;
                    color: #6a737d;
                    border-left: 0.25em solid #dfe2e5;
                }
                pre {
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 16px;
                    overflow: auto;
                }
                code {
                    font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
                    font-size: 85%;
                }
                </style>
            </head>
            <body onload="window.parent.postMessage(document.body.scrollHeight, '*')">
                ${sanitizedHtmlBody}
            </body>
            </html>
      `;
    }, [sanitizedHtmlBody]);

    const resizeIframe = useCallback(() => {
        if (iframeRef.current?.contentWindow) {
          const height = iframeRef.current.contentWindow.document.documentElement.getBoundingClientRect().height;
          iframeRef.current.style.height = `${height}px`;
        }
    }, [iframeRef]);

    useEffect(() => {
        window.addEventListener('resize', resizeIframe);
        return () => window.removeEventListener('resize', resizeIframe);
    }, []);

    return (
        <iframe
            ref={iframeRef}
            className="thread-message__body"
            srcDoc={wrappedHtml}
            sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
            onLoad={resizeIframe}
        />
    )
}

export default MessageBody;
