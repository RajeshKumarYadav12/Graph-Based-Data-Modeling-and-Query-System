<!-- Environment Configuration - Injected by build process -->
<script>
  // Load configuration from environment variables (for Vercel/build systems)
  // Or use defaults for local development
  
  if (!window.__CONFIG__) {
    window.__CONFIG__ = {
      // Try to get from environment variable (injected by Vercel build)
      api_base: globalThis.REACT_APP_API_BASE || 
                (typeof process !== 'undefined' && process.env?.REACT_APP_API_BASE) ||
                'http://localhost:8000',
    };
  }
  
  console.log('✓ Configuration loaded:', window.__CONFIG__);
</script>
