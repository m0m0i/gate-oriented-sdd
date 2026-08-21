Review this diff:

```diff
+async function loadConfig(path: string) {
+  try {
+    const raw = await fs.readFile(path, 'utf8');
+    return JSON.parse(raw) as Config;
+  } catch (e) {
+    console.log('config load failed', e);
+    return {} as Config;
+  }
+}
```

Report your findings.
