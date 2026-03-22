
let carrito = JSON.parse(localStorage.getItem('carrito')) || [];

function actualizarCarrito(){
    const lista = document.querySelector("#lista-carrito");

    
    lista.innerHTML = "";

    let total = 0;

    carrito.forEach((item) => {
        const li = document.createElement("li");

        li.textContent = `${item.nombre} - $${item.precio.toLocaleString()} `;
        lista.appendChild(li);
        total += item.precio;
    });

    document.querySelector("#total").innerHTML = total.toLocaleString();
}

document.addEventListener("DOMContentLoaded", () => {
    actualizarCarrito();

    document.querySelector("#form-compra").addEventListener("submit", (e) => {
        e.preventDefault();

        const direccion = document.querySelector("#direccion").value.trim();
        const medioPago = document.querySelector("#medioPago").value.trim();
        const fecha = document.querySelector("#fechaEntrega").value.trim();

        if (direccion && medioPago && fecha) {
           
            localStorage.removeItem('carrito');
            carrito = [];

            
            document.querySelector("#msg-confirmacion").style.display = "block";

            
            e.target.reset();

           
            document.querySelector("#lista-carrito").innerHTML = '';
            document.querySelector("#total").innerHTML = '0';
        }
    });
});


function agregarAlCarrito(nombre, precio, imagen) {
  const producto = { nombre, precio, imagen };
  let carrito = JSON.parse(localStorage.getItem("carritoTech")) || [];
  carrito.push(producto);
  localStorage.setItem("carritoTech", JSON.stringify(carrito));
  alert(`${nombre} fue agregado al carrito 🛒`);
}
