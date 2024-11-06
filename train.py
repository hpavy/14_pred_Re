import torch
from model import pde
import numpy as np
import time
from utils import read_csv, write_csv
from pathlib import Path


def train(
    nb_epoch,
    train_loss,
    test_loss,
    poids,
    model,
    loss,
    optimizer,
    X_train,
    U_train,
    X_test_pde,
    X_test_data,
    U_test_data,
    X_pde,
    Re,
    time_start,
    f,
    x_std,
    y_std,
    u_mean,
    v_mean,
    p_std,
    t_std,
    u_std,
    v_std,
    folder_result,
    save_rate,
    batch_size,
    scheduler,
):
    nb_it_tot = nb_epoch + len(train_loss["total"])
    print(
        f"--------------------------\nStarting at epoch: {len(train_loss['total'])}"
        + "\n--------------------------"
    )
    print(
        f"--------------------------\nStarting at epoch: {len(train_loss['total'])}\n------------"
        + "--------------",
        file=f,
    )

    for epoch in range(len(train_loss["total"]), nb_it_tot):
        loss_batch_train = {"total": [], "data": [], "pde": []}
        loss_batch_test = {"total": [], "data": [], "pde": []}
        for batch in range(len(X_pde) // batch_size):
            model.train()  # on dit qu'on va entrainer (on a le dropout)
            ## loss du pde
            X_pde_batch = X_pde[batch * batch_size : (batch + 1) * batch_size, :]
            pred_pde_tot = model(X_pde_batch)
            pred_pde = pred_pde_tot[:, :3]
            Re_pred = pred_pde_tot[:, 3].mean()
            pred_pde1, pred_pde2, pred_pde3 = pde(
                pred_pde,
                X_pde_batch,
                Re=Re*Re_pred,
                x_std=x_std,
                y_std=y_std,
                u_mean=u_mean,
                v_mean=v_mean,
                p_std=p_std,
                t_std=t_std,
                u_std=u_std,
                v_std=v_std,
            )
            loss_pde = (
                torch.mean(pred_pde1**2)
                + torch.mean(pred_pde2**2)
                + torch.mean(pred_pde3**2)
            )

            # loss des points de data
            pred_data_tot = model(X_train)
            pred_data = pred_data_tot[:, :3]
            loss_data = loss(U_train, pred_data)  # (MSE)
            loss_totale = poids[0] * loss_data + poids[1] * loss_pde

            # Backpropagation
            loss_totale.backward(retain_graph=True)
            optimizer.step()
            optimizer.zero_grad()
            with torch.no_grad():
                loss_batch_train["total"].append(loss_totale.item())
                loss_batch_train["data"].append(loss_data.item())
                loss_batch_train["pde"].append(loss_pde.item())

        # Pour le test :
        model.eval()

        # loss du pde
        test_pde_tot = model(X_test_pde)
        test_pde = test_pde_tot[:, :3]
        test_pde1, test_pde2, test_pde3 = pde(
            test_pde,
            X_test_pde,
            Re=Re,
            x_std=x_std,
            y_std=y_std,
            u_mean=u_mean,
            v_mean=v_mean,
            p_std=p_std,
            t_std=t_std,
            u_std=u_std,
            v_std=v_std,
        )
        loss_test_pde = (
            torch.mean(test_pde1**2)
            + torch.mean(test_pde2**2)
            + torch.mean(test_pde3**2)
        )
        # loss de la data
        test_data_tot = model(X_test_data)
        test_data = test_data_tot[:,:3]
        loss_test_data = loss(U_test_data, test_data)  # (MSE)

        # loss totale
        loss_test = poids[0] * loss_test_data + poids[1] * loss_test_pde
        scheduler.step()
        with torch.no_grad():
            test_loss["total"].append(loss_test.item())
            test_loss["data"].append(loss_test_data.item())
            test_loss["pde"].append(loss_test_pde.item())
            train_loss["total"].append(np.mean(loss_batch_train["total"]))
            train_loss["data"].append(np.mean(loss_batch_train["data"]))
            train_loss["pde"].append(np.mean(loss_batch_train["pde"]))

        print(f"---------------------\nEpoch {epoch+1}/{nb_it_tot} :")
        print(f"---------------------\nEpoch {epoch+1}/{nb_it_tot} :", file=f)
        print(
            f"Train : loss: {train_loss['total'][-1]:.3e}, data: {train_loss['data'][-1]:.3e}, pde: {train_loss['pde'][-1]:.3e}"
        )
        print(
            f"Train : loss: {train_loss['total'][-1]:.3e}, data: {train_loss['data'][-1]:.3e}, pde: {train_loss['pde'][-1]:.3e}",
            file=f,
        )
        print(
            f"Test  : loss: {test_loss['total'][-1]:.3e}, data: {test_loss['data'][-1]:.3e}, pde: {test_loss['pde'][-1]:.3e}, Re: {Re*test_pde_tot[:,3].mean()}, std: {Re*test_pde_tot[:,3].std()}"
        )
        print(
            f"Test  : loss: {test_loss['total'][-1]:.3e}, data: {test_loss['data'][-1]:.3e}, pde: {test_loss['pde'][-1]:.3e}, Re: {Re*test_pde_tot[:,3].mean()}, std: {Re*test_pde_tot[:,3].std()}",
            file=f,
        )

        print(f"time: {time.time()-time_start:.0f}s")
        print(f"time: {time.time()-time_start:.0f}s", file=f)

        if (epoch + 1) % save_rate == 0:
            dossier_midle = Path(folder_result + f"/epoch{len(train_loss['total'])}")
            dossier_midle.mkdir(parents=True, exist_ok=True)
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "scheduler_state_dict": scheduler.state_dict(),
                },
                folder_result
                + f"/epoch{len(train_loss['total'])}"
                + "/model_weights.pth",
            )

            write_csv(
                train_loss,
                folder_result + f"/epoch{len(train_loss['total'])}",
                file_name="/train_loss.csv",
            )
            write_csv(
                test_loss,
                folder_result + f"/epoch{len(train_loss['total'])}",
                file_name="/test_loss.csv",
            )
