document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("registro-form");
  const inputs = form.querySelectorAll("input, select");
  const btnEnviar = document.getElementById("btn-enviar");
  const mensaje = document.getElementById("mensaje");

  const validators = {
    nombre: (val) => /^[a-zA-ZÁÉÍÓÚáéíóúñÑ\s]{3,}$/.test(val),
    apellido: (val) => /^[a-zA-ZÁÉÍÓÚáéíóúñÑ\s]{4,}$/.test(val),
    "tipo-doc": (val) => val !== "",
    documento: (val) => /^\d{7,10}$/.test(val),
    correo: (val) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(val),
    "confirmar-correo": () =>
      document.getElementById("confirmar-correo").value ===
      document.getElementById("correo").value,
    telefono: (val) => /^\d{10}$/.test(val),
    direccion: (val) => val.trim().length >= 8,
    password: (val) =>
      /[A-Z]/.test(val) &&
      /[a-z]/.test(val) &&
      /[0-9]/.test(val) &&
      /[\W_]/.test(val) &&
      val.length >= 8,
    "confirmar-password": () =>
      document.getElementById("confirmar-password").value ===
      document.getElementById("password").value,
  };

  function validar(input) {
    const id = input.id;
    if (!id) {
      return true; // Ignorar inputs sin id para evitar error
    }
    const val = input.value.trim();
    const icono = document.getElementById(`icono-${id}`);
    const error = document.getElementById(`error-${id}`);

    let esValido = false;
    if (validators[id]) {
      if (validators[id].length === 0) {
        esValido = validators[id]();
      } else {
        esValido = validators[id](val);
      }
    }

    console.log(`Validando campo ${id}: ${esValido}`);

    if (icono) {
      input.classList.toggle("valid", esValido);
      input.classList.toggle("invalid", !esValido);
    }

    if (error) {
      error.classList.toggle("valid", esValido);
    }

    if (id === "password") {
      const lengthValid = val.length >= 8;
      const upperValid = /[A-Z]/.test(val);
      const lowerValid = /[a-z]/.test(val);
      const digitValid = /[0-9]/.test(val);
      const specialValid = /[\W_]/.test(val);
      
      document.querySelector('[data-req="length"]').classList.toggle("valid", lengthValid);
      document.querySelector('[data-req="upper"]').classList.toggle("valid", upperValid);
      document.querySelector('[data-req="lower"]').classList.toggle("valid", lowerValid);
      document.querySelector('[data-req="digit"]').classList.toggle("valid", digitValid);
      document.querySelector('[data-req="special"]').classList.toggle("valid", specialValid);
      
      // Verificar si todos los requisitos están completos
      const allComplete = lengthValid && upperValid && lowerValid && digitValid && specialValid;
      const passwordRequisitos = document.querySelector('.password-requisitos');
      
      if (passwordRequisitos) {
        if (allComplete) {
          // Aplicar la clase de éxito y ocultar después de la animación
          passwordRequisitos.classList.add('all-complete');
          // Ocultar después de 1.5 segundos para que se vea la animación
          setTimeout(() => {
            passwordRequisitos.style.display = 'none';
          }, 1500);
        } else {
          // Mostrar de nuevo si no están todos completos
          passwordRequisitos.style.display = 'block';
          passwordRequisitos.classList.remove('all-complete');
        }
      }
    }

    return esValido;
  }

  function validarTodo() {
    const resultados = Array.from(inputs).map((input) => {
      const resultado = validar(input);
      if (!resultado) {
        console.warn(`Campo inválido: ${input.id}`);
      }
      return resultado;
    });
    return resultados.every(Boolean);
  }

  inputs.forEach((input) => {
    if (input.tagName.toLowerCase() === "select") {
      input.addEventListener("change", () => {
        validar(input);
        btnEnviar.disabled = !validarTodo();
      });
    } else {
      input.addEventListener("input", () => {
        validar(input);
        btnEnviar.disabled = !validarTodo();
      });

      input.addEventListener("blur", () => {
        validar(input);
        btnEnviar.disabled = !validarTodo();
      });
    }
  });

  btnEnviar.disabled = !validarTodo();

  form.addEventListener("submit", (e) => {
    if (!validarTodo()) {
      e.preventDefault();
      mensaje.textContent = "Por favor, corrige los errores en el formulario.";
      mensaje.className = "mensaje-confirmacion mensaje-error";
    } else {
      mensaje.textContent = "";
      mensaje.className = "mensaje-confirmacion";
    }
  });
});
