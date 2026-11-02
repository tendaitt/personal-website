# tendaimudyiwa.com

Personal site of Tendai Mudyiwa. Plain HTML and CSS, hosted on GitHub Pages.

## Pages

- `index.html`: About (the landing page)
- `hello/index.html`: Say hello (served at `/hello/`)

## Publishing

1. Push this folder to a GitHub repository.
2. In the repository, go to **Settings → Pages**, choose **Deploy from a branch**, branch `main`, folder `/ (root)`.
3. The `CNAME` file sets the custom domain to `www.tendaimudyiwa.com`.
4. At your DNS provider, add:
   - `A` records for `@`: `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
   - `CNAME` record for `www`: `<your-github-username>.github.io`
5. Once DNS has updated, tick **Enforce HTTPS** in **Settings → Pages**.
