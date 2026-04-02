import javax.swing.*;
import java.awt.*;

public class GeneratedUI {
    public static void main(String[] args) {
        SwingUtilities.invokeLater(() -> createAndShowGUI());
    }

    private static void createAndShowGUI() {
        JFrame frame = new JFrame("Generated UI");
        frame.setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        frame.setSize(400, 500);

        JPanel panel = new JPanel();
        panel.setLayout(new GridLayout(0, 1, 5, 5));
        panel.setBorder(BorderFactory.createEmptyBorder(20, 20, 20, 20));

        JLabel emailLabel = new JLabel("Email");
        panel.add(emailLabel);
        JTextField emailField = new JTextField();
        panel.add(emailField);

        JLabel confirmpasswordLabel = new JLabel("Confirm Password");
        panel.add(confirmpasswordLabel);
        JPasswordField confirmpasswordField = new JPasswordField();
        panel.add(confirmpasswordField);

        JLabel newpasswordLabel = new JLabel("New Password");
        panel.add(newpasswordLabel);
        JPasswordField newpasswordField = new JPasswordField();
        panel.add(newpasswordField);

        JButton forgotpasswordBtn = new JButton("Forgot Password");
        panel.add(forgotpasswordBtn);

        JButton resetpasswordBtn = new JButton("Reset Password");
        panel.add(resetpasswordBtn);

        frame.getContentPane().add(panel);
        frame.setVisible(true);
    }
}