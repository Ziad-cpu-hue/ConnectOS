/* ─── CURSOR ─── */
const cur = document.getElementById("cur");
const ring = document.getElementById("cur-ring");
let mx = 0,
	my = 0,
	rx = 0,
	ry = 0;
document.addEventListener("mousemove", (e) => {
	mx = e.clientX;
	my = e.clientY;
	cur.style.left = mx + "px";
	cur.style.top = my + "px";
});
(function loop() {
	rx += (mx - rx) * 0.12;
	ry += (my - ry) * 0.12;
	ring.style.left = rx + "px";
	ring.style.top = ry + "px";
	requestAnimationFrame(loop);
})();
document.querySelectorAll("a,button").forEach((el) => {
	el.addEventListener("mouseenter", () => {
		ring.style.width = "46px";
		ring.style.height = "46px";
		ring.style.opacity = ".55";
	});
	el.addEventListener("mouseleave", () => {
		ring.style.width = "30px";
		ring.style.height = "30px";
		ring.style.opacity = ".3";
	});
});

/* ─── NAV SCROLL ─── */
const nav = document.getElementById("main-nav");
window.addEventListener("scroll", () => {
	nav.classList.toggle("scrolled", window.scrollY > 60);
});

/* ─── SCROLL REVEAL ─── */
const obs = new IntersectionObserver(
	(entries) => {
		entries.forEach((e, i) => {
			if (e.isIntersecting)
				setTimeout(() => e.target.classList.add("visible"), i * 55);
		});
	},
	{ threshold: 0.07 }
);
document
	.querySelectorAll(".reveal,.reveal-left")
	.forEach((el) => obs.observe(el));

/* ─── CATEGORY FILTER ─── */
const filterBtns = document.querySelectorAll(".cat-btn");
const menuCards = document.querySelectorAll(".menu-card");

filterBtns.forEach((btn) => {
	btn.addEventListener("click", () => {
		filterBtns.forEach((b) => b.classList.remove("active"));
		btn.classList.add("active");
		const filter = btn.dataset.filter;
		menuCards.forEach((card) => {
			const match = filter === "all" || card.dataset.cat === filter;
			if (match) {
				card.classList.remove("hidden");
				card.style.animation = "none";
				card.offsetHeight;
				card.style.animation = "card-in .35s both";
			} else {
				card.classList.add("hidden");
			}
		});
	});
});

/* ─── NAV CAT LINKS ─── */
const navLinks = document.querySelectorAll(".nav-cats a[data-cat]");
navLinks.forEach((a) => {
	a.addEventListener("click", (e) => {
		e.preventDefault();
		navLinks.forEach((l) => l.classList.remove("active"));
		a.classList.add("active");
		const cat = a.dataset.cat;
		const map = {
			sandwiches: "sandwich",
			bowls: "bowl",
			sides: "side",
			drinks: "drink"
		};
		const filterVal = map[cat];
		filterBtns.forEach((b) => {
			if (b.dataset.filter === filterVal) b.click();
		});
		document.getElementById("menu").scrollIntoView({ behavior: "smooth" });
	});
});

/* ─── ADD BUTTON FEEDBACK ─── */
document.querySelectorAll(".add-btn").forEach((btn) => {
	btn.addEventListener("click", () => {
		const orig = btn.innerHTML;
		btn.innerHTML =
			'<svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" fill="none" stroke-width="2.2"><polyline points="20 6 9 17 4 12"/></svg> تمام!';
		btn.style.background = "var(--teal)";
		btn.style.color = "#fff";
		setTimeout(() => {
			btn.innerHTML = orig;
			btn.style.background = "";
			btn.style.color = "";
		}, 1800);
	});
});

/* ─── MOBILE MENU ─── */
const mobileNav = document.getElementById("mobileNav");
let menuOpen = false;
function toggleMenu(btn) {
	menuOpen = !menuOpen;
	const spans = btn.querySelectorAll("span");
	if (menuOpen) {
		mobileNav.style.display = "flex";
		requestAnimationFrame(() => mobileNav.classList.add("open"));
		spans[0].style.transform = "rotate(45deg) translate(4px, 4px)";
		spans[1].style.opacity = "0";
		spans[2].style.transform = "rotate(-45deg) translate(4px,-4px)";
		document.body.style.overflow = "hidden";
	} else {
		closeMobileNav();
	}
}
function closeMobileNav() {
	menuOpen = false;
	mobileNav.classList.remove("open");
	setTimeout(() => {
		mobileNav.style.display = "none";
	}, 300);
	document.body.style.overflow = "";
	const spans = document.querySelector(".hamburger").querySelectorAll("span");
	spans[0].style.transform = "";
	spans[1].style.opacity = "";
	spans[2].style.transform = "";
}

/* ─── PARALLAX HERO ─── */
document.addEventListener("mousemove", (e) => {
	const bg = document.querySelector(".hero-bg-img");
	if (!bg) return;
	const x = (e.clientX / window.innerWidth - 0.5) * 14;
	const y = (e.clientY / window.innerHeight - 0.5) * 10;
	bg.style.transform = `translate(${x}px, ${y}px) scale(1.08)`;
});
