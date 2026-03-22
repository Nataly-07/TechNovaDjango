// Variables globales - usar las del window si existen
var estadoActual = window.estadoActual || 'todas';

// Verificar que el script se carga correctamente
console.log('✅ Script atencion-cliente.js cargado');
console.log('Estado actual:', window.estadoActual || estadoActual);
console.log('Usuario ID:', window.usuarioId);

// Funciones globales - deben estar en el scope global
window.filtrarPorEstado = function(estado) {
  var busqueda = document.getElementById('searchInput') ? document.getElementById('searchInput').value : '';
  var url = '/empleado/atencion-cliente?estado=' + encodeURIComponent(estado);
  if (busqueda) {
    url += '&busqueda=' + encodeURIComponent(busqueda);
  }
  window.location.href = url;
}

window.filtrarPorTarjeta = function(tab, filtro) {
  // Si es de la sección de mensajes, cambiar a la tab de mensajes directos
  if (tab === 'mensajes') {
    window.cambiarTab('mensajes');
    // Aquí se implementará el filtrado de mensajes directos más adelante
    return;
  }
  
  // Si es de la sección de consultas, cambiar a la tab de consultas y aplicar filtro
  if (tab === 'consultas') {
    window.cambiarTab('consultas');
    
    // Mapear el filtro según la tarjeta seleccionada
    var estadoFiltro = 'todas';
    if (filtro === 'pendientes') {
      estadoFiltro = 'pendientes'; // El backend manejará esto correctamente
    } else if (filtro === 'todas') {
      estadoFiltro = 'todas';
    }
    
    window.filtrarPorEstado(estadoFiltro);
  }
}

window.filtrarTickets = function() {
  var busqueda = document.getElementById('searchInput') ? document.getElementById('searchInput').value : '';
  var estado = window.estadoActual || estadoActual || 'todas';
  var url = '/empleado/atencion-cliente?estado=' + encodeURIComponent(estado);
  if (busqueda) {
    url += '&busqueda=' + encodeURIComponent(busqueda);
  }
  window.location.href = url;
}

window.cambiarTab = function(tab) {
  if (tab === 'consultas') {
    var tabs = document.querySelectorAll('.tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.remove('active');
    }
    if (tabs[0]) tabs[0].classList.add('active');
    var consultasFilters = document.getElementById('consultasFilters');
    if (consultasFilters) consultasFilters.style.display = 'flex';
    var ticketsList = document.getElementById('ticketsList');
    if (ticketsList) ticketsList.style.display = 'block';
    var mensajesList = document.getElementById('mensajesList');
    if (mensajesList) mensajesList.style.display = 'none';
  } else if (tab === 'mensajes') {
    var tabs = document.querySelectorAll('.tab');
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.remove('active');
    }
    if (tabs[1]) tabs[1].classList.add('active');
    var consultasFilters = document.getElementById('consultasFilters');
    if (consultasFilters) consultasFilters.style.display = 'none';
    var ticketsList = document.getElementById('ticketsList');
    if (ticketsList) ticketsList.style.display = 'none';
    var mensajesList = document.getElementById('mensajesList');
    if (mensajesList) mensajesList.style.display = 'block';
  }
}

// Mostrar detalle de ticket
window.mostrarDetalleTicket = function(ticketId) {
  fetch('/api/atencion-cliente/' + ticketId)
    .then(function(response) {
      if (!response.ok) {
        throw new Error('Error al cargar el ticket');
      }
      return response.json();
    })
    .then(function(data) {
      var modal = document.getElementById('ticketModal');
      var title = document.getElementById('modalTicketTitle');
      var content = document.getElementById('modalTicketContent');
      
      title.textContent = data.tema || 'Sin tema';
      
      var nombresUsuarios = window.nombresUsuarios || {};
      var clienteNombre = nombresUsuarios && nombresUsuarios[data.usuarioId] ? nombresUsuarios[data.usuarioId] : (data.usuarioId ? 'Usuario ID: ' + data.usuarioId : 'Usuario desconocido');
      var fecha = data.fechaConsulta ? new Date(data.fechaConsulta).toLocaleString('es-ES') : 'N/A';
      
      var estadoClass = data.estado || 'abierto';
      var estadoTexto = data.estado || 'Abierto';
      var descripcion = data.descripcion || 'Sin descripción';
      var respuestaHtml = '';
      
      if (data.respuesta) {
        respuestaHtml = 
          '<div style="background: #e8f5e8; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745;">' +
            '<h4 style="color: #28a745; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;">' +
              '<i class=\'bx bx-check-circle\'></i> Respuesta:' +
            '</h4>' +
            '<p style="color: #2c3e50; line-height: 1.6; margin: 0;">' +
              data.respuesta +
            '</p>' +
          '</div>';
      } else {
        respuestaHtml = 
          '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border: 2px dashed #dee2e6; text-align: center;">' +
            '<i class=\'bx bx-time\' style="font-size: 2rem; color: #6c757d; margin-bottom: 10px; display: block;"></i>' +
            '<p style="color: #6c757d; margin: 0;">Esta consulta aún no tiene respuesta.</p>' +
            '<button onclick="window.responderTicket(' + data.id + ')" class="btn-primary" style="margin-top: 15px;">' +
              '<i class=\'bx bx-reply\'></i> Responder' +
            '</button>' +
          '</div>';
      }
      
      content.innerHTML = 
        '<div style="margin-bottom: 20px;">' +
          '<div style="display: flex; gap: 15px; margin-bottom: 15px; flex-wrap: wrap;">' +
            '<span style="display: flex; align-items: center; gap: 5px; color: #6c757d; font-size: 0.9rem;">' +
              '<i class=\'bx bx-calendar\'></i> ' + fecha +
            '</span>' +
            '<span style="display: flex; align-items: center; gap: 5px; color: #6c757d; font-size: 0.9rem;">' +
              '<i class=\'bx bx-user\'></i> ' + clienteNombre +
            '</span>' +
            '<span class="ticket-status ' + estadoClass + '" style="font-size: 0.8rem;">' +
              estadoTexto +
            '</span>' +
          '</div>' +
          '<div style="margin-bottom: 20px;">' +
            '<h4 style="color: #2c3e50; margin-bottom: 10px;">Descripción:</h4>' +
            '<p style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #667eea; color: #495057; line-height: 1.6;">' +
              descripcion +
            '</p>' +
          '</div>' +
          respuestaHtml +
        '</div>';
      
      modal.style.display = 'flex';
    })
    .catch(function(error) {
      console.error('Error:', error);
      alert('Error al cargar el ticket: ' + error.message);
    });
}

window.cerrarModalTicket = function() {
  document.getElementById('ticketModal').style.display = 'none';
}

window.responderTicket = function(ticketId) {
  var respuesta = prompt('Ingresa tu respuesta:');
  if (!respuesta || respuesta.trim() === '') {
    return;
  }
  
  var formData = new URLSearchParams();
  formData.append('respuesta', respuesta.trim());
  
  fetch('/api/atencion-cliente/' + ticketId + '/responder', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: formData.toString()
  })
  .then(function(response) {
    if (!response.ok) {
      throw new Error('Error al responder el ticket');
    }
    return response.json();
  })
  .then(function(data) {
    alert('Respuesta enviada correctamente');
    window.cerrarModalTicket();
    location.reload();
  })
  .catch(function(error) {
    console.error('Error:', error);
    alert('Error al responder el ticket: ' + error.message);
  });
}

// Funcionalidad de conversaciones
var currentConversationId = null;
var currentMessageId = null;
var nombresUsuarios = window.nombresUsuarios || {};

window.showConversation = function(conversationId, messageId) {
  currentConversationId = conversationId;
  currentMessageId = messageId;
  
  var modal = document.getElementById('conversationModal');
  var messagesContainer = document.getElementById('conversationMessages');
  
  modal.style.display = 'flex';
  messagesContainer.innerHTML = '<div class="conversation-empty"><i class="bx bx-loader-alt bx-spin"></i><p>Cargando conversación...</p></div>';
  
  window.loadConversation(conversationId);
}

window.closeConversationModal = function() {
  document.getElementById('conversationModal').style.display = 'none';
  currentConversationId = null;
  currentMessageId = null;
}

window.loadConversation = function(conversationId) {
  fetch('/api/mensajes-directos/conversacion/' + conversationId)
    .then(function(response) {
      if (!response.ok) {
        throw new Error('Error al cargar la conversación');
      }
      return response.json();
    })
    .then(function(data) {
      if (data.error) {
        throw new Error(data.error);
      }
      window.displayConversation(data);
    })
    .catch(function(error) {
      console.error('Error:', error);
      document.getElementById('conversationMessages').innerHTML = 
        '<div class="conversation-empty"><i class="bx bx-error"></i><p>Error al cargar la conversación</p></div>';
    });
}

window.displayConversation = function(messages) {
  var messagesContainer = document.getElementById('conversationMessages');
  
  if (!messages || messages.length === 0) {
    messagesContainer.innerHTML = 
      '<div class="conversation-empty"><i class="bx bx-message-square-dots"></i><p>No hay mensajes en esta conversación</p></div>';
    return;
  }

  // Actualizar currentMessageId con el ID del último mensaje para responder
  if (messages.length > 0) {
    var lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.id) {
      currentMessageId = lastMessage.id;
    }
  }

  messagesContainer.innerHTML = '';
  
  messages.forEach(function(message) {
    var isSent = message.senderType === 'empleado';
    var messageElement = document.createElement('div');
    messageElement.className = 'message-bubble ' + (isSent ? 'sent' : 'received');
    
    var fecha = message.createdAt ? new Date(message.createdAt).toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }) : 'N/A';
    
    var senderName = isSent ? 'Tú' : (message.userId && nombresUsuarios[message.userId] ? nombresUsuarios[message.userId] : 'Cliente');
    
    messageElement.innerHTML = 
      '<div class="message-avatar">' + (isSent ? '👨‍💼' : '👤') + '</div>' +
      '<div class="message-content">' +
        '<div style="font-size: 0.75rem; opacity: 0.8; margin-bottom: 4px;">' + senderName + '</div>' +
        '<div class="message-text">' + (message.mensaje || 'Sin mensaje') + '</div>' +
        '<div class="message-time">' + fecha + '</div>' +
      '</div>';
    
    messagesContainer.appendChild(messageElement);
  });
  
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Responder en conversación
document.addEventListener('DOMContentLoaded', function() {
  var conversationReplyForm = document.getElementById('conversationReplyForm');
  if (conversationReplyForm) {
    conversationReplyForm.addEventListener('submit', function(e) {
      e.preventDefault();
      
      if (!currentMessageId) {
        alert('Error: No se puede responder sin un mensaje seleccionado');
        return;
      }
      
      var mensaje = document.getElementById('conversationReplyText').value.trim();
      
      if (!mensaje) {
        alert('Por favor escribe un mensaje');
        return;
      }
      
      var usuarioId = window.usuarioId || null;
      
      var formData = new URLSearchParams();
      formData.append('senderId', usuarioId.toString());
      formData.append('senderType', 'empleado');
      formData.append('mensaje', mensaje);
      
      var sendBtn = document.getElementById('conversationSendBtn');
      sendBtn.disabled = true;
      sendBtn.innerHTML = '<i class="bx bx-loader-alt bx-spin"></i> Enviando...';
      
      fetch('/api/mensajes-directos/' + currentMessageId + '/responder', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData.toString()
      })
      .then(function(response) {
        if (response.ok) {
          document.getElementById('conversationReplyText').value = '';
          window.loadConversation(currentConversationId);
          alert('Mensaje enviado correctamente');
        } else {
          return response.text().then(function(errorText) {
            alert('Error al enviar el mensaje: ' + errorText);
          });
        }
      })
      .catch(function(error) {
        console.error('Error:', error);
        alert('Error al enviar el mensaje: ' + error.message);
      })
      .finally(function() {
        sendBtn.disabled = false;
        sendBtn.innerHTML = '<i class="bx bx-send"></i> Enviar';
      });
    });
  }

  // Cerrar modal al hacer clic fuera
  var ticketModal = document.getElementById('ticketModal');
  if (ticketModal) {
    ticketModal.addEventListener('click', function(e) {
      if (e.target === this) {
        window.cerrarModalTicket();
      }
    });
  }

  var conversationModal = document.getElementById('conversationModal');
  if (conversationModal) {
    conversationModal.addEventListener('click', function(e) {
      if (e.target === this) {
        window.closeConversationModal();
      }
    });
  }

  // Marcar el filtro activo según el estado actual
  // Marcar botones de filtro activos
  var estado = window.estadoActual || estadoActual || 'todas';
  var filterBtns = document.querySelectorAll('.filter-btn');
  for (var i = 0; i < filterBtns.length; i++) {
    var btn = filterBtns[i];
    btn.classList.remove('active');
    var btnText = btn.textContent.trim().toLowerCase();
    if ((estado === 'todas' && btnText === 'todas') ||
        (estado === 'abierto' && btnText === 'pendientes') ||
        (estado === 'en_proceso' && btnText === 'en proceso') ||
        (estado === 'resuelto' && btnText === 'resueltas') ||
        (estado === 'cerrado' && btnText === 'cerradas')) {
      btn.classList.add('active');
    }
  }

  // Marcar tarjetas de estadísticas activas
  var activeTab = document.querySelector('.tab.active');
  var tabActual = activeTab ? 
    (document.querySelectorAll('.tab')[0].classList.contains('active') ? 'consultas' : 'mensajes') : 'consultas';
  
  var statCards = document.querySelectorAll('.stat-card');
  for (var j = 0; j < statCards.length; j++) {
    var card = statCards[j];
    card.classList.remove('active-filter');
    var tabCard = card.getAttribute('data-tab');
    var filtro = card.getAttribute('data-filtro');
    
    // Solo marcar como activa si está en la tab correcta
    if (tabCard === tabActual) {
      // Para consultas
      if (tabCard === 'consultas') {
        if ((estado === 'todas' && filtro === 'todas') ||
            (estado === 'pendientes' && filtro === 'pendientes')) {
          card.classList.add('active-filter');
        }
      }
      // Para mensajes (se implementará más adelante)
      // Por ahora, si estamos en la tab de mensajes, no marcamos ninguna como activa
    }
  }
  
  // Verificar que las funciones estén disponibles
  console.log('✅ Funciones disponibles:', {
    filtrarPorEstado: typeof window.filtrarPorEstado,
    filtrarPorTarjeta: typeof window.filtrarPorTarjeta,
    cambiarTab: typeof window.cambiarTab,
    filtrarTickets: typeof window.filtrarTickets,
    mostrarDetalleTicket: typeof window.mostrarDetalleTicket
  });
});

