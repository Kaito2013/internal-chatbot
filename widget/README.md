# Internal Chatbot Widget

A lightweight, self-contained Vanilla JS chat widget for embedding on any website. No build tools, no dependencies, just a single script tag.

## Features

- **Self-contained**: Pure Vanilla JS, no frameworks or build tools required
- **Session Management**: Automatic session creation and persistence with localStorage
- **Dark Theme**: Modern, sleek design optimized for contemporary websites
- **Auth Support**: JWT token authentication via `window.chatbotConfig`
- **Responsive**: Adapts to mobile and desktop screens
- **Accessible**: ARIA labels, keyboard navigation, focus states
- **Public API**: Programmatic control via `window.Chatbot`

## Installation

### Option 1: Direct Copy

1. Copy `widget.js` and `widget.css` to your website's directory
2. Add the script tag to your HTML

```html
<script src="widget.js" 
        data-api-url="https://api.yourchatbot.com"
        data-chatbot-id="your-chatbot-id"
        data-position="right"></script>
```

### Option 2: CDN (if you host the files)

```html
<script src="https://cdn.yourdomain.com/widget.js" 
        data-api-url="https://api.yourchatbot.com"
        data-position="right"></script>
```

## Configuration

### Script Tag Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `data-api-url` | string | required | Base URL of your chatbot API |
| `data-chatbot-id` | string | empty | Optional chatbot identifier |
| `data-position` | string | `"right"` | Widget position: `"left"` or `"right"` |
| `data-offset-bottom` | number | `20` | Bottom offset in pixels |
| `data-offset-right` | number | `20` | Right offset in pixels |
| `data-offset-left` | number | `20` | Left offset in pixels |

### Global Configuration (`window.chatbotConfig`)

Set this before the widget script loads:

```javascript
window.chatbotConfig = {
  // Authentication
  authToken: 'your-jwt-token',  // Optional: sent as Bearer token
  
  // User info
  email: 'user@example.com',    // Optional: sent to API
  
  // Custom offsets
  offset: {
    bottom: 20,
    right: 20,
    left: 20
  },
  
  // Session expiry in ms (default: 24 hours)
  sessionExpiry: 24 * 60 * 60 * 1000
};
```

## Public API

Access the widget instance via `window.Chatbot`:

```javascript
// Open/close the widget
window.Chatbot.open();
window.Chatbot.close();
window.Chatbot.toggle();

// Clear chat history
window.Chatbot.clearHistory();

// Send a message programmatically
window.Chatbot.sendMessage('Hello!');

// Get current session
const session = window.Chatbot.getSession();
console.log(session.id, session.history);

// Access configuration
const config = window.Chatbot.config;
```

## Events

Listen to widget events:

```javascript
// Message sent or received
window.Chatbot.on('message', (data) => {
  console.log('Message:', data.text, 'Role:', data.role);
});

// Session created (first visit or expired)
window.Chatbot.on('sessionCreate', (session) => {
  console.log('New session:', session.id);
});
```

## API Integration

### Request Format

The widget sends a POST request to `{apiUrl}/api/chat`:

```json
{
  "session_id": "sess_abc123_xyz789",
  "question": "Hello, how can you help me?",
  "user_id": null,
  "email": "user@example.com"
}
```

**Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer {token}` (if `authToken` configured)

### Response Format

Your API should return:

```json
{
  "answer": "Hello! I'm here to help you with...",
  "sources": ["Document 1", "FAQ Page"],
  "used_crm": true
}
```

### Error Handling

For errors, you can:

1. Return an error in the response:
```json
{
  "error": "Unable to process request"
}
```

2. The widget will display error messages gracefully

3. Network errors show a generic "try again" message

## Customization

### CSS Variables

Override these variables to customize the appearance:

```css
.chatbot-widget {
  --cb-primary: #1a1a1a;        /* Main background */
  --cb-secondary: #2d2d2d;      /* Header, input area */
  --cb-border: #3d3d3d;         /* Borders */
  --cb-text: #e5e5e5;           /* Primary text */
  --cb-text-muted: #888888;     /* Muted text */
  --cb-accent: #4f46e5;         /* Accent color (buttons, user bubbles) */
  --cb-accent-hover: #4338ca;   /* Accent hover state */
  --cb-radius: 12px;            /* Border radius */
  --cb-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
}
```

### Example: Green Theme

```css
.chatbot-widget {
  --cb-accent: #10b981;
  --cb-accent-hover: #059669;
}
```

### Position

Use `data-position="left"` or `data-position="right"`:

```html
<script src="widget.js" data-position="left" ...></script>
```

## Session Management

- Sessions are stored in `localStorage` under key `chatbot_session_id`
- Each session contains: `id`, `userId`, `created`, `expires`, `history`
- Sessions expire after 24 hours (configurable)
- History is preserved across page reloads within the session

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

## File Structure

```
widget/
├── widget.js      # Main widget script (contains embedded styles)
├── widget.css     # Reference stylesheet (optional)
├── example.html   # Integration example with mock API
└── README.md      # This file
```

## Troubleshooting

### Widget not appearing

1. Check browser console for errors
2. Verify `data-api-url` is set correctly
3. Ensure the script tag is placed before `</body>`

### API requests failing

1. Check CORS configuration on your API
2. Verify the API URL is correct (include protocol)
3. Check if auth token is valid

### Styles look wrong

1. Ensure no other CSS is overriding widget styles
2. Use higher specificity selectors if needed:
```css
body .chatbot-widget {
  --cb-accent: #your-color;
}
```

### Session not persisting

- Check if localStorage is enabled
- Incognito/private mode may block localStorage

## License

Internal use - Your Company Name

---

For support, contact your development team.
