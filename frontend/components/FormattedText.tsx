// Simple markdown formatter for chat responses
function parseSimpleMarkdown(text: string): string {
  let html = text;

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3 style="margin: 1rem 0 0.5rem; font-size: 1.125rem; font-weight: 600; color: #111;">$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2 style="margin: 1.25rem 0 0.75rem; font-size: 1.25rem; font-weight: 600; color: #111;">$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1 style="margin: 1.5rem 0 1rem; font-size: 1.5rem; font-weight: 700; color: #111;">$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong style="font-weight: 600;">$1</strong>');
  
  // Italic
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Code blocks (```code```)
  html = html.replace(/```([\s\S]*?)```/g, '<pre style="background: #f3f4f6; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; margin: 1rem 0;"><code>$1</code></pre>');
  
  // Inline code (`code`)
  html = html.replace(/`([^`]+)`/g, '<code style="background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.9em;">$1</code>');
  
  // Unordered lists (- item or * item)
  html = html.replace(/^[\-\*] (.+)$/gim, '<li style="margin-left: 1.5rem;">$1</li>');
  html = html.replace(/(<li[^>]*>.*<\/li>)/s, '<ul style="margin: 0.5rem 0; padding-left: 0;">$1</ul>');
  
  // Numbered lists (1. item)
  html = html.replace(/^\d+\. (.+)$/gim, '<li style="margin-left: 1.5rem;">$1</li>');
  
  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" style="color: #6366f1; text-decoration: underline;">$1</a>');
  
  // Line breaks (double newline = paragraph break)
  html = html.replace(/\n\n/g, '<br><br>');
  html = html.replace(/\n/g, '<br>');

  return html;
}

export default function FormattedText({ content }: { content: string }) {
  const htmlContent = parseSimpleMarkdown(content);
  
  return (
    <div 
      style={{
        lineHeight: 1.6,
        fontSize: '1rem',
        color: '#374151'
      }}
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}