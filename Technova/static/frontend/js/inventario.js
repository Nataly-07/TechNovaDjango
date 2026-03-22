const form = document.getElementById('formProducto');
const tbody = document.getElementById('tbodyProductos');
const filtroInput = document.getElementById('buscarProducto');
const filtroCategoria = document.getElementById('filtroCategoria');
const contador = document.getElementById('contadorProductos');

let productos = JSON.parse(localStorage.getItem('productosTech')) || [];

function renderProductos(lista) {
  tbody.innerHTML = '';
  lista.forEach((prod, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${prod.nombre}</td>
      <td>${prod.marca}</td>
      <td>$${prod.precio.toLocaleString()}</td>
      <td>${prod.stock}</td>
      <td>${prod.categoria}</td>
      <td><button onclick="eliminar(${index})">Eliminar</button></td>
    `;
    tbody.appendChild(tr);
  });
  contador.textContent = `Total: ${lista.length} productos`;
}

form.addEventListener('submit', e => {
  e.preventDefault();
  const producto = {
    nombre: nombre.value.trim(),
    marca: marca.value.trim(),
    precio: Number(precio.value),
    stock: Number(stock.value),
    categoria: categoria.value
  };
  productos.push(producto);
  localStorage.setItem('productosTech', JSON.stringify(productos));
  renderProductos(productos);
  form.reset();
});

function eliminar(index) {
  Swal.fire({
    title: '¿Eliminar producto?',
    text: 'Esta acción no se puede deshacer',
    icon: 'warning',
    showCancelButton: true,
    confirmButtonText: 'Sí, eliminar'
  }).then(result => {
    if (result.isConfirmed) {
      productos.splice(index, 1);
      localStorage.setItem('productosTech', JSON.stringify(productos));
      renderProductos(productos);
    }
  });
}

filtroInput.addEventListener('input', () => {
  const texto = filtroInput.value.toLowerCase();
  const filtrados = productos.filter(p => p.nombre.toLowerCase().includes(texto));
  renderProductos(filtrados);
});

filtroCategoria.addEventListener('change', () => {
  const categoria = filtroCategoria.value;
  const filtrados = categoria === 'todos'
    ? productos
    : productos.filter(p => p.categoria === categoria);
  renderProductos(filtrados);
});

renderProductos(productos);
