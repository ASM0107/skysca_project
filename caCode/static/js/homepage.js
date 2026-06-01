document.addEventListener("DOMContentLoaded", () => {
  // Get logo elements
  const logo = document.querySelector(".logo");
  const logoText = document.querySelector(".logo-text");

  // Logo → Homepage
  [logo, logoText].forEach((el) => {
    if (el) {
      el.style.cursor = "pointer";
      el.addEventListener("click", () => {
        window.location.href = "/";
      });
    }
  });

  // Header Navigation Links
  const navLinks = document.querySelectorAll("nav a");
  navLinks.forEach((navLink) => {
    const text = navLink.textContent.trim().toLowerCase();
    switch (text) {
      case "certificates":
        navLink.href = "/certificates/";
        break;
      case "support":
        navLink.href = "/support/";
        break;
      case "about":
        navLink.href = "/about/";
        break;
    }
  });

  // Login button
  const loginBtn = document.querySelector(".loginbtn");
  if (loginBtn) {
    loginBtn.addEventListener("click", () => {
      window.location.href = "/login/";
    });
  }

  // CTA / Learn More → Certificates page
  document.querySelectorAll(".btn-outline").forEach((btn) => {
    if (btn.textContent.includes("Learn More")) {
      btn.addEventListener("click", () => {
        window.location.href = "/certificates/";
      });
    }
  });

  // Signup redirection from a form
  const nextStepBtn = document.querySelector(".next-step");
  const domainInput = document.querySelector(".domain-input");

  if (nextStepBtn && domainInput) {
    nextStepBtn.addEventListener("click", () => {
      const domain = domainInput.value.trim();
      if (domain === "") {
        alert("Please enter your domain name.");
      } else {
        window.location.href = "/signup/";
      }
    });
  }

  // Footer Links
  document.querySelectorAll("footer a").forEach((link) => {
    const text = link.textContent.trim().toLowerCase();
    if (
      text.includes("ssl") ||
      text.includes("code signing") ||
      text.includes("multi-domain")
    ) {
      link.href = "/certificates/";
    } else if (
      text.includes("installation") ||
      text.includes("support") ||
      text.includes("help")
    ) {
      link.href = "/support/";
    } else if (
      text.includes("about") ||
      text.includes("company") ||
      text.includes("privacy") ||
      text.includes("terms")
    ) {
      link.href = "/about/";
    }
  });
});
