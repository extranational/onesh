# This One Command Reveals EVERYTHING About a Domain (DNS enumeration with `dig`)

- **Channel:** The Cyber Hub
- **Video:** https://www.youtube.com/watch?v=ABQtVxwD6j8
- **Length:** ~21 min
- **Original language:** Hindi (Hinglish)
- **Topic:** Enumerating a DNS service (port 53) with the `dig` tool, ending in a DNS zone transfer

---

## Summary

A practical walkthrough of the **`dig`** ("Domain Information Groper") tool for DNS enumeration during a pentest. Scenario: an Nmap scan finds ports 22 (SSH), 25 (SMTP), 53 (DNS), 80 (HTTP) open — how do you enumerate the DNS service on port 53?

It first explains **how DNS works** (domain → IP resolution via the local cache → ISP resolver → root → TLD → authoritative name servers). Then it demonstrates `dig` commands:

- `dig google.com` / `dig google.com A` → IPv4 address(es) (multiple IPs for load balancing)
- `dig google.com AAAA` → IPv6
- `dig google.com NS` → name servers
- `dig google.com MX` → mail servers (e.g. smtp.google.com)
- `dig google.com TXT` → TXT records
- `dig -x <IP>` → **reverse lookup** (IP → domain)
- `dig @8.8.8.8 …` / `@1.1.1.1` → query a **specific** resolver (Google / Cloudflare) instead of your ISP's
- `+short` → terse output
- `dig <ns> <domain> AXFR` → **DNS zone transfer**

The payoff is the **zone transfer (AXFR)**: against Google's well-configured servers it's refused, but against the target lab's misconfigured DNS server it succeeds and **dumps the full zone** — revealing hidden subdomains (`dnsmanager.`, `ticketsystem.`, `urlanalyzer.`, `admin.` of `hopaitech.thm`). These are then added to `/etc/hosts` so the attacker can reach those URLs. The lesson: a misconfigured server that answers AXFR requests leaks its entire domain table.

---

## Full English Translation

Consider a situation: you're doing penetration testing on some network, and suddenly you get an IP. After doing an Nmap scan on this IP, you get this result — you can see **port 22 is open, port 25 is open, port 53 is open, and port 80 is open.** Now, 22 is for SSH, 25 is for SMTP, 80 is for HTTP, and you can clearly see a **DNS service** running on **port 53.** Now my question is: how will you enumerate this and attack it? Let's find out.

To enumerate this particular port 53, we'll use a tool called the **`dig`** tool. The full form of this tool is **Domain Information Groper.** If you just `man` it, you'll get all the information. Let me explain how this tool works. It simply tells you the **corresponding IP for a domain** — it's a DNS lookup utility.

But you'll ask, what is DNS? DNS is simply the **Domain Naming System.** How does it work? Consider it like a big phone book for the internet. We know domain names like google.com, microsoft.com, openai.com, etc. To work, browsers need an **IP** to make a request and get a response. To get the IP corresponding to a domain name, **DNS** comes in between. First, your system checks whether google.com was ever requested before (cache). If not, it goes to your **ISP provider's DNS service** — your internet provider (Jio, Airtel, whatever Wi-Fi service you use; these are ISPs, Internet Service Providers). From there a **hierarchy** is followed: for google.com, it first goes to the **root name server** (which says which server handles `.com`), then we get the IPs of the servers that hold the `.com` thing, then we go to the **TLD name servers**, where we get the **name-server IP of google.com**. That name server holds the IPs of google.com's resources, and from that name server we get the google.com IP we'll reach. This is how a DNS query actually works.

Now, if I just write `dig google.com`, it gives me the results. We can see the **status is NOERROR** — meaning it successfully found this domain's IP. The question asked is google.com's IPv4 address, and the answer part is google.com's IPv4 address. Why "A"? It's the standard — the standard for an IPv4 address. You can simply write `A` here too and get proper output. Here you can see a lot of IPs — Google uses many IPs to balance traffic. Every domain has IPv4 and corresponding IPv6 too. For the IPv6 address, just write `AAAA` (four A's) and you'll get the IPv6 address.

Now you might ask: is the `dig` tool only used for translation (resolution)? No — we can use it to find **mail servers, name servers, and many other things.** As we know from DNS, what are name servers? Name servers are the servers that actually keep these IPs. Let's find out which name servers Google has. Write `dig google.com NS` — here you can see the name-server IPs along with the names. This particular NS is google.com's name server; this is its IPv4 address, and this is its name (the domain name given to this name server).

Let's find out: if you mail someone on the google.com domain, to which server is the mail actually requesting — where is the mail going? Just write `MX` — it shows you the mail servers, and the name of this mail server is smtp.google.com. Now we know that with `dig` we can find a domain's IP, find where the IP is actually being fetched from (name servers), find mail servers under the domain, and find IPv6 addresses. There are a few other things like `TXT` — if some file is stored, it shows you like this (TXT files stored).

Now, using `dig` we can also do a **reverse lookup** — you have an IP and you can find the domain. If I write `dig google.com`, take whatever IP I'm getting, pick any one (the first), then write `dig -x <IP>` (keep in mind it's a small `x`) — it shows me the name. It didn't say google.com, but it shows me this name, because on this particular domain Google will respond to me. We can also see `dig -x 8.8.8.8` — this is a DNS server of Google. If you request any address on this particular server for DNS resolution, it'll find you the IPv4/IPv6 address, mail servers, and NS servers. It shows the domain name associated with this particular IP.

Now this is a very long output — we can make it short. `dig google.com MX +short` shows only the name. If you want only this name, write `+short`; if you want the whole thing, write it without it (shows name, IP, everything). Similarly for `NS` — shows all the name-server names. To find the IPs of google.com, you can get all the IPs. This is the benefit of `+short` — verbose output isn't shown.

After that, the most important utility: in the DNS part we already discussed how DNS works. Whenever you request `dig google.com`, it goes to a particular DNS service — your ISP's (Internet Service Provider's) DNS — which searches the domain name's IP and sends it to you. The DNS servers, just like Google's DNS server **8.8.8.8** and Cloudflare's **1.1.1.1** — 8.8.8.8 is Google's, 1.1.1.1 is Cloudflare's. If you don't want to use your ISP's DNS server, you can do the DNS query on any of the free public DNS servers. There's an option in `dig` for this: `dig @1.1.1.1 google.com` — you'll get the same response. (It shows a slightly different IP because the lookup is done a different way — completely fine.) Write `@8.8.8.8` — if you write NS, it shows name servers; mail servers, it shows the mail server. Everything works, but you're not using your ISP's domain resolution — you're using **Google's DNS service.** That's the benefit of `dig`.

And lastly, the most important thing. These **name servers** hold every IP of google.com — every service's IP of google.com. All the IPs we get for Google (mail servers, resolution servers, anything) are present inside these name servers. If a malicious actor could **dump** this name server's IPs (all of google.com's IPs), they'd simply get all the domains and domain names with their IPs. To do this we write `dig <name-server> <domain> AXFR`. Mention any one name server — I'll name it `ns1.google.com`, because this server has the target IPs — then `google.com`, then `AXFR`. If you hit enter you'll get a **"transfer failed"** result, because this server is well protected and configured; no name resolution will leak from it, because this is a **potential threat.** This is what we call a **zone transfer** — more precisely, a **DNS zone transfer.**

What have we learned? If we have a domain name, we can find its IP (IPv4), find its IPv6 address, find its name servers, find its mail servers. We can make the response short with the `+short` flag. If we have its IPv4/IPv6 address we can get the domain name via reverse lookup `-x`. We can use any specific DNS server — our ISP's or any available (Google, Cloudflare). And we learned `AXFR`, the DNS zone transfer.

Now let's come back to our target topic — our target work. We have a domain service running in this particular server. Let's enumerate. From **web enumeration** (the website open on port 80) I got some information — let me show you: I've got eight emails / email IDs, and from that I can easily see its name is something like `hopaitech.` (a domain name). What I did: `sudo mousepad /etc/hosts` and added this IP with this domain name. My target is to find what more information is in this domain server.

From the lab environment I know this is a standalone machine and its mail server and name server will be in this same IP. (I won't enumerate further; if you're pentesting a network, **always enumerate for name servers and mail servers.**) I'll directly jump to a **DNS zone transfer** to find which other domains are available in this particular DNS service. I write `dig`, then mention the IP — my IP here is 10.49.143.138 (this is the name server's / DNS server's IP) — then the domain name `hopaitech.thm`, then the zone-transfer command `AXFR`, and hit enter.

You'll see a magic: we knew this domain, but we got something even more advanced — we got **DNS Manager** (hopaitech), **Ticket System** (hopaitech), **URL Analyzer** (hopaitech), and **admin** (hopaitech). We got these four domains, and this is the list — a complete table that this DNS service was holding, and it's leaked now. Because that DNS server has some **misconfigurations** / permission issues, so whenever anyone asks for a zone transfer, it simply responds — there's a problem in it, and because of that problem we're getting this response.

I'll take the names — `admin.hopaitech.thm`, `dnsmanager`, `ticketsystem`, `urlanalyzer` — and paste them into `/etc/hosts` so I can access these particular URLs / domain names.

So this is how you can use the `dig` tool (Domain Information Groper) to enumerate the DNS service. There are a lot of ways to do this. This is a very small video, and in it I've explained as much as possible about DNS and how to get DNS grouping information. I hope you liked this video — if you did, do like, share, and subscribe to the channel. See you soon.
