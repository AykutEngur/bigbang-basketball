// Big Bang Basketball - front-end behaviors

document.addEventListener("DOMContentLoaded", function () {

  // --- Mobil nav toggle ---
  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");

  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  // --- Profil dropdown ---
  var profileBtn = document.getElementById("nav-profile-btn");
  var dropdown = document.getElementById("nav-dropdown");
  var profileWrapper = document.getElementById("nav-profile-wrapper");

  if (profileBtn && dropdown) {
    profileBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = dropdown.classList.contains("open");
      dropdown.classList.toggle("open");
      profileBtn.setAttribute("aria-expanded", !isOpen);
    });

    // Disariya tiklayinca kapat
    document.addEventListener("click", function (e) {
      if (profileWrapper && !profileWrapper.contains(e.target)) {
        dropdown.classList.remove("open");
        profileBtn.setAttribute("aria-expanded", "false");
      }
    });

    // Escape ile kapat
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        dropdown.classList.remove("open");
        profileBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // --- Sozlesme modal (register ve create-team sayfalarinda) ---
  var openBtn = document.getElementById("open-contract-modal");
  var closeBtn = document.getElementById("close-contract-modal");
  var acceptBtn = document.getElementById("accept-contract-btn");
  var overlay = document.getElementById("contract-modal-overlay");
  var checkbox = document.getElementById("contract_accepted");

  function openModal() {
    if (overlay) overlay.classList.add("open");
  }

  function closeModal() {
    if (overlay) overlay.classList.remove("open");
  }

  if (openBtn) {
    openBtn.addEventListener("click", function (e) {
      e.preventDefault();
      openModal();
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", closeModal);
  }

  if (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closeModal();
    });
  }

  if (acceptBtn) {
    acceptBtn.addEventListener("click", function () {
      if (checkbox) checkbox.checked = true;
      closeModal();
    });
  }

  // --- Federasyon sayfasi scroll animasyonlari ---
  var animated = document.querySelectorAll(
    ".animate-fade-up, .animate-slide-left, .animate-slide-right"
  );

  if (animated.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );

    animated.forEach(function (el) {
      if (el.closest(".fed-hero") || el.closest(".fed-stats-band")) return;
      observer.observe(el);
    });
  }

});