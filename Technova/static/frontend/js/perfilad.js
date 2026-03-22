document.addEventListener('DOMContentLoaded', function () {
  function openTab(evt, tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(function (tabContent) {
      tabContent.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(function (tabButton) {
      tabButton.classList.remove('active');
    });

    // Show the selected tab content and set the button active
    document.getElementById(tabName).classList.add('active');
    evt.currentTarget.classList.add('active');
  }

  // Attach openTab function to window for inline onclick usage
  window.openTab = openTab;

  // User search filter
  const buscadorUsuarios = document.getElementById('buscadorUsuarios');
  const usuariosBody = document.getElementById('usuarios-body');
  const filtroRol = document.getElementById('filtroRol');
  const contadorUsuarios = document.getElementById('contadorUsuarios');

  function filterUsers() {
    const searchTerm = buscadorUsuarios.value.toLowerCase();
    const roleFilter = filtroRol.value;
    let visibleCount = 0;

    usuariosBody.querySelectorAll('tr').forEach(function (row) {
      const nombre = row.cells[0].textContent.toLowerCase();
      const correo = row.cells[1].textContent.toLowerCase();
      const rol = row.cells[2].textContent.toLowerCase();

      const matchesSearch = nombre.includes(searchTerm) || correo.includes(searchTerm);
      const matchesRole = roleFilter === 'todos' || rol === roleFilter;

      if (matchesSearch && matchesRole) {
        row.style.display = '';
        visibleCount++;
      } else {
        row.style.display = 'none';
      }
    });

    contadorUsuarios.textContent = 'Total de usuarios: ' + visibleCount;
  }

  buscadorUsuarios.addEventListener('input', filterUsers);
  filtroRol.addEventListener('change', filterUsers);

  // Product search filter
  const buscadorProductos = document.getElementById('buscadorProductos');
  const productosTable = document.querySelector('.table-inventario tbody');

  function filterProducts() {
    const searchTerm = buscadorProductos.value.toLowerCase();

    productosTable.querySelectorAll('tr').forEach(function (row) {
      const codigo = row.cells[0].textContent.toLowerCase();
      const nombre = row.cells[1].textContent.toLowerCase();
      const categoria = row.cells[3].textContent.toLowerCase();
      const marca = row.cells[8].textContent.toLowerCase();

      const matchesSearch = codigo.includes(searchTerm) || nombre.includes(searchTerm) || categoria.includes(searchTerm) || marca.includes(searchTerm);

      if (matchesSearch) {
        row.style.display = '';
      } else {
        row.style.display = 'none';
      }
    });
  }

  buscadorProductos.addEventListener('input', filterProducts);
});
