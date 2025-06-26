# 5 laboratorinis darbas - Mongo DB
## Trip Registry
### The service allows navigation devices to record trips.

1. **Register a new client**  
   URL: `/clients`  
   Method: `PUT`  
   Parameters:  

   | **Parameter** | **Type**  | **In**  | **Required** |
   |---------------|-----------|---------|--------------|
   | `firstName`   | string    | body    | yes          |
   | `lastName`    | string    | body    | yes          |
   | `email`       | string    | body    | yes          |
   | `dateOfBirth` | string    | body    | yes          |
   | `id`          | string    | body    | no           |

   Responses:  

   | **Response**     | **Description**                               |
   |------------------|-----------------------------------------------|
   | `201` `clientId` | Client registered.                            |
   | `400`            | Invalid input or missing required fields.     |

2. **Get client details**  
   URL: `/clients/{clientId}`  
   Method: `GET`  
   Parameters:  

   | **Parameter**    | **Type**  | **In**  | **Required** |
   |------------------|-----------|---------|--------------|
   | `clientId`       | string    | path    | yes          |
   | `includeVehicles`| bool      | query   | no           |

   Responses:  

   | **Response**  | **Description**            |
   |---------------|----------------------------|
   | `200`         | Client details.            |
   | `404`         | Client not found.          |

3. **Register a vehicle**  
   URL: `/clients/{clientId}/vehicles`  
   Method: `PUT`  
   Parameters:  

   | **Parameter**   | **Type**  | **In**  | **Required** |
   |-----------------|-----------|---------|--------------|
   | `clientId`      | string    | path    | yes          |
   | `model`         | string    | body    | yes          |
   | `make`          | string    | body    | yes          |
   | `VIN`           | string    | body    | yes          |
   | `licensePlateNo`| string    | body    | yes          |
   | `year`          | integer   | body    | yes          |
   | `id` (vehicle)  | string    | body    | no           |

   Responses:  

   | **Response**        | **Description**                                 |
   |---------------------|-------------------------------------------------|
   | `201` `vehicleId`   | Vehicle registered.                             |
   | `400`               | Invalid input or missing required fields.       |
   | `404`               | Client not found.                               |

4. **Get client's vehicles**  
   URL: `/clients/{clientId}/vehicles`  
   Method: `GET`  
   Parameters:  

   | **Parameter**   | **Type**  | **In**  | **Required** |
   |-----------------|-----------|---------|--------------|
   | `clientId`      | string    | path    | yes          |

   Responses:  

   | **Response**  | **Description**             |
   |---------------|-----------------------------|
   | `200`         | Vehicles list.              |
   | `204`         | Client has no vehicles.     |
   | `404`         | Client not found.           |

5. **Get vehicle details**  
   URL: `/clients/{clientId}/vehicles/{vehicleId}`  
   Method: `GET`  
   Parameters:  

   | **Parameter**   | **Type**  | **In**  | **Required** |
   |-----------------|-----------|---------|--------------|
   | `clientId`      | string    | path    | yes          |
   | `vehicleId`     | string    | path    | yes          |

   Responses:  

   | **Response**  | **Description**                   |
   |---------------|-----------------------------------|
   | `200`         | Vehicle details.                  |
   | `404`         | Client or vehicle not found.      |

6. **Register (start) a new trip**  
   URL: `/trips`  
   Method: `PUT`  
   Parameters:  

   | **Parameter**   | **Type**              | **In**  | **Required** |
   |-----------------|-----------------------|---------|--------------|
   | `clientId`      | string                | body    | yes          |
   | `vehicleId`     | string                | body    | yes          |
   | `coordinates`   | list of integers      | body    | yes          |

   Responses:  

   | **Response**   | **Description**                                 |
   |----------------|-------------------------------------------------|
   | `201` `tripId` | Trip registered.                                |
   | `400`          | Invalid input or missing required fields.       |
   | `404`          | Client or vehicle not found.                    |

7. **Get client's trips**  
   URL: `/clients/{clientId}/trips`  
   Method: `GET`  
   Parameters:  

   | **Parameter**   | **Type**     | **In**   | **Required** |
   |-----------------|--------------|----------|--------------|
   | `clientId`      | string       | path     | yes          |
   | `status`        | string       | query    | no           |
   | `vehicleId`     | string       | query    | no           |
   | `startDate`     | integer      | query    | no           |
   | `endDate`       | integer      | query    | no           |

   Responses:  
   | **Response**   | **Description**                      |
   |----------------|--------------------------------------|
   | `200`          | Trip list.                           |
   | `404`          | Client or vehicle not found.         |

8. **Get trip details**  
   URL: `/clients/{clientId}/trips/{tripId}`  
   Method: `GET`  
   Parameters:  

   | **Parameter**   | **Type**     | **In**   | **Required** |
   |-----------------|--------------|----------|--------------|
   | `clientId`      | string       | path     | yes          |
   | `tripId`        | string       | path     | yes          |

   Responses:  
   | **Response**   | **Description**            |
   |----------------|----------------------------|
   | `200`          | Trips list.                 |
   | `404`          | Client not found.          |

9. **Register a position**  
   URL: `/clients/{clientId}/trips/positions`  
   Method: `PUT`  
   Parameters:  

   | **Parameter**   | **Type**        | **In**   | **Required** |
   |-----------------|-----------------|----------|--------------|
   | `clientId`      | string          | path     | yes          |
   | `coordinates`   | list of integers| body     | yes          |

   Responses:  
   | **Response**   | **Description**                              |
   |----------------|----------------------------------------------|
   | `201`          | Position registered.                         |
   | `400`          | Invalid input or missing required fields.    |
   | `404`          | Client or active trip not found.             |

10. **End trip**  
    URL: `/clients/{clientId}/trips/stop`  
    Method: `PUT`  
    Parameters:  

    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |
    | `coordinates`   | list of integers| body     | yes          |

    Responses:  
    | **Response**   | **Description**                              |
    |----------------|----------------------------------------------|
    | `200`          | Trip ended.                                  |
    | `400`          | Invalid input or missing required fields.    |
    | `404`          | Client not found.                            |

11. **Delete client's vehicles**  
    URL: `/clients/{clientId}/vehicles`  
    Method: `DELETE`  
    Parameters:  

    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |

    Responses:  
    | **Response**   | **Description**                              |
    |----------------|----------------------------------------------|
    | `204`          | Vehicles deleted.                            |
    | `404`          | Client not found.                            |

12. **Delete vehicle**  
    URL: `/clients/{clientId}/vehicles/{vehicleId}`  
    Method: `DELETE`  
    Parameters:  

    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |
    | `vehicleId`     | string          | path     | yes          |

    Responses:  
    | **Response**   | **Description**                              |
    |----------------|----------------------------------------------|
    | `204`          | Vehicle deleted.                             |
    | `404`          | Client or vehicle not found.                 |

13. **Delete client**  
    URL: `/clients/{clientId}`  
    Method: `DELETE`  
    Parameters:  

    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |

    Responses:  
    | **Response**   | **Description**                   |
    |----------------|-----------------------------------|
    | `204`          | Client deleted.                   |

14. **Get total distance**  
    URL: `/distance/{clientId}`  
    Method: `GET`  
    Parameters:  

    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |
    | `tripId`        | string          | query    | no           |
    | `vehicleId`     | string          | query    | no           |

    Responses:  
    | **Response**   | **Description**                        |
    |----------------|----------------------------------------|
    | `200`          | Total distance.                        |
    | `404`          | Client, vehicle, or trip not found.    |

15. **Get total duration**  
    URL: `/duration/{clientId}`  
    Method: `GET`  
    Parameters:  
    | **Parameter**   | **Type**        | **In**   | **Required** |
    |-----------------|-----------------|----------|--------------|
    | `clientId`      | string          | path     | yes          |
    | `tripId`        | string          | query    | no           |
    | `vehicleId`     | string          | query    | no           |

    Responses:  
    | **Response**   | **Description**                        |
    |----------------|----------------------------------------|
    | `200`          | Total duration.                        |
    | `404`          | Client, vehicle, or trip not found.    |

16. **Cleanup**  
    URL: `/cleanup`  
    Method: `POST`  
    Parameters: `None`  

    Responses:  
    | **Response**   | **Description**       |
    |----------------|-----------------------|
    | `204`          | Cleanup successful.   |
